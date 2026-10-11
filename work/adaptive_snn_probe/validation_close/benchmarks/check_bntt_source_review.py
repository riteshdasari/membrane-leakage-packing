"""Bounded source/data-metadata audit; never import Torch or execute a model."""
import ast
import copy
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def strip_cuda(node):
    # Independent structural construction, without importing the adapter.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'cuda':
        assert not node.args and not node.keywords
        return strip_cuda(node.func.value)
    if isinstance(node, ast.AST):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                setattr(node, field, [strip_cuda(v) for v in value])
            elif isinstance(value, ast.AST):
                setattr(node, field, strip_cuda(value))
    return node


def main():
    acquisition = json.loads((P / 'bntt_acquisition.json').read_text())
    source_checks = {name: sha(P / 'bntt_visual_source' / name) == expected
                     for name, expected in acquisition['source_files_sha256'].items()}
    asset_checks = {item['filename']: sha(P / item['filename']) == item['sha256']
                    for item in acquisition['assets']}
    assert all(source_checks.values()) and all(asset_checks.values())
    files = ['bntt_integer.py', 'run_bntt.py', 'ottt_integer_v2.py',
             'bntt_visual_source/model.py', 'bntt_visual_source/main.py',
             'bntt_visual_source/utils.py']
    syntax = {}
    for filename in files:
        tree = ast.parse((P / filename).read_text())
        compile(tree, filename, 'exec')  # Syntax only: no exec/import of source.
        syntax[filename] = True
    original = ast.parse((P / 'bntt_visual_source/model.py').read_text())
    calls = [node for node in ast.walk(original) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == 'cuda']
    assert all(not node.args and not node.keywords for node in calls)
    cpu = strip_cuda(copy.deepcopy(original))
    assert not any(isinstance(node, ast.Attribute) and node.attr == 'cuda' for node in ast.walk(cpu))
    compile(ast.fix_missing_locations(cpu), 'independent_expected_cpu_port', 'exec')
    expected_cpu_ast_hash = hashlib.sha256(ast.dump(cpu, include_attributes=False).encode()).hexdigest()
    original_forward = next(node for node in ast.walk(original)
                            if isinstance(node, ast.FunctionDef) and node.name == 'forward'
                            and any(isinstance(k, ast.arg) and k.arg == 'target_layer' for k in node.args.args))
    original_bn = sorted({node.value.attr for node in ast.walk(original_forward)
                          if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                          and node.value.attr.startswith('bn')})
    assert original_bn == ['bn1_list', 'bn2_list', 'bn3_list', 'bn4_list', 'bn5_list',
                           'bn6_list', 'bn7_list', 'bn8_list', 'bnfc_list']
    # Independent integer arithmetic: this is not a model forward or source execution.
    mismatches = sum((-((-253 * u) // 256)) != (u - ((3 * u) // 256))
                     for u in range(-32768, 32768))
    assert mismatches == 0
    assert -131072 <= 3 * -32768 and 3 * 32767 < 131072
    assert round(.99 * 256) == 253
    declared = json.loads((P / 'bntt_predeclared_subset.json').read_text())
    selected = np.sort(np.random.default_rng(20211001).choice(10000, 64, replace=False))
    assert selected.tolist() == [sample['canonical_index'] for sample in declared['samples']]
    with zipfile.ZipFile(P / 'tiny-imagenet-200.zip') as archive:
        classes = sorted(archive.read('tiny-imagenet-200/wnids.txt').decode().splitlines())
        annotations = {r[0]: r[1] for r in
                       (line.split('\t') for line in archive.read('tiny-imagenet-200/val/val_annotations.txt').decode().splitlines())}
        assert len(classes) == len(set(classes)) == 200 and len(annotations) == 10000
        class_to_idx = {name: index for index, name in enumerate(classes)}
        samples = []
        for sample in declared['samples']:
            index = sample['canonical_index']
            filename = f'val_{index}.JPEG'
            assert sample['filename'] == filename
            assert sample['class_id'] == annotations[filename]
            assert sample['class_index'] == class_to_idx[annotations[filename]]
            assert sample['poisson_seed'] == 2021 + index
            jpeg = archive.read('tiny-imagenet-200/val/images/' + filename)
            samples.append({'index': index, 'label': sample['class_index'],
                            'jpeg_sha256': hashlib.sha256(jpeg).hexdigest()})
    result = {'status': 'passed_bounded_source_and_metadata_review',
              'torch_imported': 'torch' in sys.modules, 'model_inference_performed': False,
              'vendor_tools_launched': False,
              'source_sha256': {filename: sha(P / filename) for filename in files},
              'frozen_source_hash_gates': source_checks, 'frozen_asset_hash_gates': asset_checks,
              'syntax_only_compile': syntax, 'parameterless_cuda_calls_removed': len(calls),
              'independently_expected_cpu_ast_sha256': expected_cpu_ast_hash,
              'original_per_timestep_bn_layers': original_bn,
              'beta253_constant_control': {'cases': 65536, 'mismatches': mismatches,
                                          'signed18_3U_range': [-98304, 98301]},
              'subset_and_class_metadata_verified': len(samples), 'selected_images': samples,
              'remaining_runtime_gates': ['weights_only safe-global compatibility',
                                          'strict state_dict shapes/loading',
                                          'per-update state/spike and complete logits agreement',
                                          'observed signed16 range admission',
                                          'bounded FP32 versus declared-integer conversion accuracy']}
    assert not result['torch_imported']
    (P / 'bntt_independent_source_checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in
                      ['status', 'torch_imported', 'parameterless_cuda_calls_removed',
                       'independently_expected_cpu_ast_sha256', 'beta253_constant_control',
                       'subset_and_class_metadata_verified']}, indent=2))


if __name__ == '__main__':
    main()
