# Import the Qiskit SDK
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, transpile
from qiskit.circuit import Parameter
from qiskit_aer import AerSimulator, Aer
from qiskit.qasm3 import load
import sys
from timeit import timeit

def dict_key_b2d(d: dict):
    newd = {}
    for k, v in d.items():
        # convert binary to decimal
        # qiskit put earlier defined cregs to the right (LSB).
        # we want to put earlier printed(defined) cregs to the left.
        # also, qiskit show the result of all cregs. we just want the ones printed, excluding the cond_creg.
        newd[tuple(int(s, 2) for s in reversed(k.split()[:-1]))] = v
    return newd

qc = load(sys.argv[1])

backend_sim = AerSimulator(max_parallel_threads=24, method='statevector')
isa_qc = transpile(qc, backend_sim, optimization_level=3)
#print(isa_qc.depth())

def run():
    job_sim = backend_sim.run(isa_qc, shots=1)
    result_sim = job_sim.result()
    print(dict_key_b2d(result_sim.get_counts()))

t = timeit(run, number = 1)

print('time used:', t, 's')

# job_sim = backend_sim.run(qc, shots=1)
# result_sim = job_sim.result()
# print(dict_key_b2d(result_sim.get_counts()))