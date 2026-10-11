`timescale 1ps/1ps
module tb_minimal_carry;
  reg [3:0] S=0, DI=0;
  reg CI=0, CYINIT=0;
  wire [3:0] CO, O;
  CARRY4 u(.S(S),.DI(DI),.CI(CI),.CYINIT(CYINIT),.CO(CO),.O(O));
  integer fail_count=0;
  integer cases=0;
  integer i;
  integer widths[0:7];
  reg[3:0] expect_co,expect_o;
  reg c;
  task check(input string label);
    begin
      c=CI|CYINIT;
      for(i=0;i<4;i=i+1)begin
        expect_o[i]=S[i]^c;
        expect_co[i]=S[i]?c:DI[i];
        c=expect_co[i];
      end
      cases=cases+1;
      if(CO!==expect_co || O!==expect_o)begin
        fail_count=fail_count+1;
        $display("ISOLATED_FAILURE %s T%0t S%h DI%h CI%b CYINIT%b CO%h O%h EXPECT_CO%h EXPECT_O%h",label,$time,S,DI,CI,CYINIT,CO,O,expect_co,expect_o);
      end else $display("ISOLATED_PASS %s T%0t",label,$time);
    end
  endtask
  always @(S or DI or CI or CYINIT or CO or O)
    $display("M T%0t S%h DI%h CI%b CYINIT%b CO%h O%h",$time,S,DI,CI,CYINIT,CO,O);
  initial begin
    if(!$test$plusargs("FUNCTIONAL_ONLY"))
      $sdf_annotate("carry_original_paths.sdf");
    #2000; S=7; #2000; check("stable setup");
    widths[0]=0; widths[1]=1; widths[2]=5; widths[3]=25;
    widths[4]=50; widths[5]=100; widths[6]=300; widths[7]=1000;
    for(integer w=0;w<8;w=w+1)begin
      S=0; CI=0; DI=0; #2000; S=7; #2000;
      CI=1; #(widths[w]) CI=0;
      #3000; check($sformatf("CI pulse width %0d ps",widths[w]));
    end
    S=0; CI=0; DI=0; #2000;
    #0 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11046000 ps
    #3150 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11049150 ps
    #62 S=4'h5; DI=4'h0; CI=1'b0; // row910 original 11049212 ps
    #119 S=4'h6; DI=4'h0; CI=1'b0; // row910 original 11049331 ps
    #170 S=4'h2; DI=4'h0; CI=1'b0; // row910 original 11049501 ps
    #70 S=4'h4; DI=4'h0; CI=1'b0; // row910 original 11049571 ps
    #67 S=4'h3; DI=4'h0; CI=1'b0; // row910 original 11049638 ps
    #88 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11049726 ps
    #5 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11049731 ps
    #113 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11049844 ps
    #67 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11049911 ps
    #43 S=4'h6; DI=4'h0; CI=1'b0; // row910 original 11049954 ps
    #49 S=4'h5; DI=4'h0; CI=1'b0; // row910 original 11050003 ps
    #14 S=4'h1; DI=4'h0; CI=1'b0; // row910 original 11050017 ps
    #5 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11050022 ps
    #1 S=4'h1; DI=4'h0; CI=1'b0; // row910 original 11050023 ps
    #10 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11050033 ps
    #114 S=4'h6; DI=4'h0; CI=1'b0; // row910 original 11050147 ps
    #61 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11050208 ps
    #51 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11050259 ps
    #15 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11050274 ps
    #116 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11050390 ps
    #276 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11050666 ps
    #303 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11050969 ps
    #113 S=4'h0; DI=4'h0; CI=1'b0; // row910 original 11051082 ps
    #119 S=4'h7; DI=4'h0; CI=1'b0; // row910 original 11051201 ps
    #11620 S=4'h0; DI=4'h0; CI=1'b0; // row911 original 11062821 ps
    #125 S=4'h7; DI=4'h0; CI=1'b0; // row911 original 11062946 ps
    #11631 S=4'h0; DI=4'h0; CI=1'b0; // row912 original 11074577 ps
    #386 S=4'h7; DI=4'h0; CI=1'b0; // row912 original 11074963 ps
    #9958 S=4'h6; DI=4'h0; CI=1'b0; // row913 original 11084921 ps
    #181 S=4'h7; DI=4'h0; CI=1'b0; // row913 original 11085102 ps
    #110 S=4'h5; DI=4'h0; CI=1'b0; // row913 original 11085212 ps
    #289 S=4'h1; DI=4'h0; CI=1'b0; // row913 original 11085501 ps
    #70 S=4'h3; DI=4'h0; CI=1'b0; // row913 original 11085571 ps
    #67 S=4'h2; DI=4'h0; CI=1'b0; // row913 original 11085638 ps
    #37 S=4'h0; DI=4'h0; CI=1'b0; // row913 original 11085675 ps
    #56 S=4'h1; DI=4'h0; CI=1'b0; // row913 original 11085731 ps
    #185 S=4'h5; DI=4'h0; CI=1'b0; // row913 original 11085916 ps
    #30 S=4'h3; DI=4'h0; CI=1'b0; // row913 original 11085946 ps
    #137 S=4'h4; DI=4'h0; CI=1'b0; // row913 original 11086083 ps
    #2 S=4'h0; DI=4'h0; CI=1'b0; // row913 original 11086085 ps
    #30 S=4'h1; DI=4'h0; CI=1'b0; // row913 original 11086115 ps
    #4 S=4'h0; DI=4'h0; CI=1'b0; // row913 original 11086119 ps
    #26 S=4'h6; DI=4'h0; CI=1'b0; // row913 original 11086145 ps
    #184 S=4'h7; DI=4'h0; CI=1'b0; // row913 original 11086329 ps
    #1 S=4'h6; DI=4'h0; CI=1'b0; // row913 original 11086330 ps
    #8 S=4'h7; DI=4'h0; CI=1'b0; // row913 original 11086338 ps
    #31 S=4'h0; DI=4'h0; CI=1'b0; // row913 original 11086369 ps
    #215 S=4'h1; DI=4'h0; CI=1'b0; // row913 original 11086584 ps
    #48 S=4'h0; DI=4'h0; CI=1'b0; // row913 original 11086632 ps
    #193 S=4'h6; DI=4'h0; CI=1'b0; // row913 original 11086825 ps
    #81 S=4'h7; DI=4'h0; CI=1'b0; // row913 original 11086906 ps
    #246 S=4'h6; DI=4'h0; CI=1'b0; // row913 original 11087152 ps
    #21 S=4'h7; DI=4'h0; CI=1'b0; // row913 original 11087173 ps
    #67 S=4'h0; DI=4'h0; CI=1'b0; // row913 original 11087240 ps
    #9910 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11097150 ps
    #62 S=4'h5; DI=4'h0; CI=1'b0; // row914 original 11097212 ps
    #119 S=4'h6; DI=4'h0; CI=1'b0; // row914 original 11097331 ps
    #170 S=4'h2; DI=4'h0; CI=1'b0; // row914 original 11097501 ps
    #70 S=4'h4; DI=4'h0; CI=1'b0; // row914 original 11097571 ps
    #67 S=4'h3; DI=4'h0; CI=1'b0; // row914 original 11097638 ps
    #88 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11097726 ps
    #5 S=4'h0; DI=4'h0; CI=1'b0; // row914 original 11097731 ps
    #113 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11097844 ps
    #99 S=4'h1; DI=4'h0; CI=1'b0; // row914 original 11097943 ps
    #11 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11097954 ps
    #49 S=4'h6; DI=4'h0; CI=1'b0; // row914 original 11098003 ps
    #2 S=4'h4; DI=4'h0; CI=1'b0; // row914 original 11098005 ps
    #12 S=4'h0; DI=4'h0; CI=1'b0; // row914 original 11098017 ps
    #5 S=4'h1; DI=4'h0; CI=1'b0; // row914 original 11098022 ps
    #1 S=4'h2; DI=4'h0; CI=1'b0; // row914 original 11098023 ps
    #10 S=4'h0; DI=4'h0; CI=1'b0; // row914 original 11098033 ps
    #82 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11098115 ps
    #32 S=4'h6; DI=4'h0; CI=1'b0; // row914 original 11098147 ps
    #61 S=4'h0; DI=4'h0; CI=1'b0; // row914 original 11098208 ps
    #182 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11098390 ps
    #208 S=4'h1; DI=4'h0; CI=1'b0; // row914 original 11098598 ps
    #68 S=4'h0; DI=4'h0; CI=1'b0; // row914 original 11098666 ps
    #155 S=4'h1; DI=4'h0; CI=1'b0; // row914 original 11098821 ps
    #148 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11098969 ps
    #183 S=4'h0; DI=4'h0; CI=1'b0; // row914 original 11099152 ps
    #88 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11099240 ps
    #134 S=4'h7; DI=4'h0; CI=1'b1; // row914 original 11099374 ps
    #0 S=4'h7; DI=4'h0; CI=1'b0; // row914 original 11099374 ps
    #3000;
    check("recorded row914 settled");
    $display("ISOLATION_COMPLETE cases=%0d failures=%0d",cases,fail_count);
    $finish;
  end
endmodule
