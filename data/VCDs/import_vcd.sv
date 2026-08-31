module import_vcd;

   reg clk1, clk2;
   reg A, B, C;
   reg [3:0] DATA_i;
   reg [3:0] DATA_o;


   initial begin
      clk1 = 'b0;
      clk2 = 'b0;

      B = 'bx;
      C = 'bx;
      DATA_i = 'hx;
      DATA_o = 'hx;
   end


   always begin
      #(10ns);
      clk1 = ~clk1;
   end

   always begin
      @(posedge clk1);
      clk2 = ~clk2;
   end

   initial begin
      A = 'bx;
      @(posedge clk1);
      #(2ns:2ns:4ns);
      A = 1;
      repeat(2)
	@(posedge clk1);
      #(2ns:2ns:4ns);
      A = 0;
      @(posedge clk1);
      #(3ns:3ns:4ns);
      A = 1;
      @(posedge clk1);
      #(4ns:4ns:6ns);
      A = 'bx;
   end // initial begin

   initial begin
      B = 'bx;
      @(posedge clk2);
      #(4ns:4ns:5ns);
      B = 0;
      @(posedge clk2);
      #(6ns:6ns:8ns);
      B = 1;
      @(posedge clk2);
      #(3ns:3ns:4ns);
      B = 'bz;
      @(posedge clk2);
      #(4ns:4ns:6ns);
      B = 0;
   end // initial begin

   initial begin
      C = 'bz;
      @(posedge clk2);
      #(2ns:2ns:5ns);
      C = 1;
      @(posedge clk2);
      #(5ns:5ns:7ns);
      C = 0;
      @(posedge clk2);
      #(3ns:3ns:4ns);
      C = 'bz;
      @(posedge clk2);
      #(4ns:4ns:6ns);
      C = 'bx;
   end // initial begin


   
   initial begin
      DATA_i = 'hx;
      @(posedge clk2);
      #(2ns:2ns:5ns);
      DATA_i = 'h0;
      @(posedge clk2);
      @(posedge clk2);
      #(5ns:5ns:7ns);
      DATA_i = 'hA;
      @(posedge clk2);
      @(posedge clk2);
      #(3ns:3ns:4ns);
      DATA_i = 'hz;
      @(posedge clk2);
      #(4ns:4ns:6ns);
      DATA_i = 'hx;
   end // initial begin

   
   initial begin
      DATA_o = 'hx;
      @(posedge clk1);
      #(2ns:2ns:6ns);
      DATA_o = 'h0;
      @(posedge clk1);
      @(posedge clk1);
      #(3ns:3ns:6ns);
      DATA_o = 'hA;
      @(posedge clk1);
      @(posedge clk1);
      #(3ns:3ns:5ns);
      DATA_o = 'hz;
      @(posedge clk1);
      #(4ns:4ns:6ns);
      DATA_o = 'hx;
   end // initial begin


endmodule // import_vcd

   
