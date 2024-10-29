N_lims = [30    , 300   , 600   , 900   , 1200  , 1800  , 2400  , 3000  , 6000  , 9000  , 12000 , 15000 , 18000 , 36000 , 72000 , 144000, 288000]
lrs = [0.1]*(len(N_lims))
q_skews = [20]*len(N_lims)
rst_skews = [50]*len(N_lims)
sizes = [(100000, 100), (150000, 100), (100000, 100), (100000, 100), (150000, 100), (100000, 100), (100000, 100), (100000, 100), (100000, 100), (100000, 100), (100000, 100), (200000, 100), (200000, 100), (200000, 100), (200000, 100), (200000, 100), (400000, 100)]
caps = [7]*len(N_lims)
specTXT = "FG !rst -> (GF state = 1)"
network_type = "A3-Default"
SMTencode = "new"
module_name = "Thermocouple"


import math
import time
import itertools
import sys

print("1)ABC 2)nuXmv 3)our")
ch = int(input("Enter your choice: "))
sys.path.append('../../')
if ch == 1:
	import Tools.abc_mc.abc_run as abc_run
elif ch == 2:
	import Tools.nuXmv.nuxmv_run as nuxmv_run
else:
	import Tools.neuralmc.nuR as nuR

if ch in [1, 2]:
	for dut_i in range(len(N_lims)):
		name = f"thermocouple_{dut_i+1}"
		N_lim = N_lims[dut_i]
		idtxt = f"{name} ({specTXT}) {N_lim}"
		print(idtxt)
		LTLSpec = "LTLSPEC F G (Verilog.Thermocouple.rst = FALSE) -> G F (Verilog.Thermocouple.state[1] = FALSE & Verilog.Thermocouple.state[0] = TRUE)"
		if ch == 1:
			abc_run.runABC(name, module_name, LTLSpec, idtxt)
		else: 
			nuxmv_run.runNuXmv(name, module_name, LTLSpec, idtxt)
		sys.stdout.flush()
		continue
	exit()

for dut_i in range(len(N_lims)):
	lr = lrs[dut_i]
	q_skew = q_skews[dut_i]
	rst_skew = rst_skews[dut_i]
	N_lim = N_lims[dut_i]
	smp, trace_len = sizes[dut_i]
	cap = caps[1]
	neural_network_size_mult = 1
	range_vals = iter(['Y', '0', N_lim, 'N', 'N', 'Y', rst_skew, 'N', 'N', 'N', 'N', 'N'])
	begin = time.time()

	name = f"thermocouple_{dut_i+1}"
	module_name = "Thermocouple"
	F_prec = 14
	idtxt = f"{name} ({specTXT}) {N_lim}"
	print(f"\t\t\t\t {idtxt}\n\t\t\t\t ({lr}, {q_skew}, {rst_skew}, {network_type}, ({smp}, {trace_len}), {cap})")
	#nuR.getLGC_SSS(name, module_name, idtxt)
	#exit()
	
	state_vars, inp_out_vars = nuR.readForVars(name, module_name, range_vals)
	next_power_of_2 = lambda n: 1 << (n - 1).bit_length()
	clamp_bits = max(int(math.log2(2**max([value['size'] for value in state_vars.values()])/10000)),0) + cap
	bits = max(max([value['size'] for value in state_vars.values()]), clamp_bits + 5) + F_prec + 10  # 2*F_prec as its needed for quant dot product, the max(max(), 8) as clamp is 2**8
	spec_str = ["isValid = 1;",
			   "if (q == 0 && (obj.state != 1 && rst == 0)) begin",
			   	"\tif ($urandom % 20 == 0)",
			   	 	"\t\tq = 1;",
			   	 "\telse",
			   	 	"\t\tq = 0;",
			   	 "end",
			   "else if (q == 0)",
			   	"\tq = 0;",
			   "else if (q == 1 && (obj.state != 1 && rst == 0))",
			   	"\tq = 1;", 
			   "else",
			   	"\tisValid = 0;"]
	stt_acc = [1]
	q_bits = 1
	q_max = 1
	nuR.makeVerilogSampler(name, module_name, smp, trace_len, spec_str, state_vars, inp_out_vars, stt_acc, q_bits, q_max)
	# We explicitly state the spec_vars, as its not part of the verilog
	bw_obj, curr_vars, next_vars, non_state_vars = nuR.verilogSMT(name, module_name, state_vars, bits, inp_out_vars, spec_vars = ['q'])
	ctx = state_vars, inp_out_vars, bw_obj, bits
	spec = [ [nuR.Bset(curr_vars, 'q', 0, ctx), nuR.Bset(next_vars, 'q',0, ctx)],
			 [nuR.Bset(curr_vars, 'q', 0, ctx), nuR.BUnSet(next_vars, 'state', 1, ctx), nuR.Bset(non_state_vars, 'rst', 0, ctx), nuR.Bset(next_vars, 'q', 1, ctx)],
			 [nuR.Bset(curr_vars, 'q', 1, ctx), nuR.BUnSet(next_vars, 'state', 1, ctx), nuR.Bset(non_state_vars, 'rst', 0, ctx), nuR.Bset(next_vars, 'q', 1, ctx)]]	
	
	bw_obj[2].bitwuzla().assert_formula(nuR.bOrOfAnd(spec, bw_obj))
	nuR.runExperiment(name, bw_obj, curr_vars, next_vars, non_state_vars, F_prec, bits, clamp_bits, network_type, idtxt, lr, stt_acc, q_bits, q_max, SMTencode)
	end = time.time()
	print(f"BITS ---------->>>>>>>>> {bits} {idtxt}")
	print(f"Total Time: {end - begin}")
