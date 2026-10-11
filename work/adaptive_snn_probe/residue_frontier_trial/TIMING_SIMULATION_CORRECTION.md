# Standalone timing simulation correction

The first frontier timing elaborations omitted AMD UG900's required
interconnect transport and zero pulse rejection options. Three a1 routed
replays initially reported valid-output mismatches; E4 subsequently did too.
E0/E1 completed their comparisons. None
of those activities are accepted for a publication energy comparison.

The first v3 correction added `-transport_int_delays -pulse_r 0 -pulse_int_r 0`
and explicit `-maxdelay`, but left the pulse error limits at their default100.
All seven attempts failed their comparisons with unknown arithmetic/control
values, and none is accepted. The complete v4 runners now also set
`-pulse_e 0 -pulse_int_e 0`, matching the complete standalone command shown by
AMD support. The v4 auditors require all four zero settings and slow/max.
No timing checks, SDF annotation, warnings, assertions, trace rows or valid
results are disabled. All six original engines and the F5 sibling are repeated
with the same method. RTL, checkpoints, clock period/phase, full input trace,
sampling rule and activity interval remain unchanged. The archived runs,
including failed data comparisons and preliminary E0 power, remain available.

Source: AMD UG900, Running Timing Simulation Using Third-Party Tools:
https://docs.amd.com/r/2025.1-English/ug900-vivado-logic-simulation/Running-Timing-Simulation-Using-Third-Party-Tools
Options: https://docs.amd.com/r/2025.2-English/ug900-vivado-logic-simulation/xelab-xvhdl-and-xvlog-xsim-Command-Options
AMD support's complete standalone command:
https://adaptivesupport.amd.com/s/question/0D5KZ00000d1YGP0A2/postimplementation-timing-simulation%E7%BB%93%E6%9E%9C%E4%B8%8E%E9%A2%84%E6%9C%9F%E4%B8%8D%E7%AC%A6?language=ja

This correction also means previously archived selective/operand-isolation
activity estimates using the omitted switches are preliminary; do not reuse
their numeric energy comparison as final paper evidence without repeating
them. Their native arithmetic checks and routed resource/timing reports are
separate evidence and are not changed by simulator pulse handling.
