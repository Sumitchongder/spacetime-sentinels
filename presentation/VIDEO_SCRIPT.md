# Video walkthrough: script and shot list

**Target length:** 9 to 10 minutes. **Speakers:** Sumit Tapas Chongder (S) and Aditya Kumar (A).
**Screen:** slides from `presentation/slides.pdf`, the live game at `https://Sumitchongder.github.io/spacetime-sentinels/`, and a terminal.
**Recording tips:** 1080p, OBS or Zoom screen recording, one take per section, keep the cursor slow. Upload the final MP4 to YouTube (unlisted) or to a GitHub Release, and paste the link into the README section "Video walkthrough".

The judges weight *Presentation* at 40 %: they want each game rule mapped to the physics, the design choices justified, and honest limitations. Every section below is written for that.

---

## 0:00 to 0:40 · Hook (S, slide 1 then the game)

> Hi, we are Sumit and Aditya from IIT Jodhpur. This is Spacetime Sentinels, a game about error detection with spacetime codes, where every single score is computed by Qiskit. Let me show you the move that surprised us most.
>
> *(Game: Deep 18, 16 T gates, post sentinels on q0, q2, q4, choose Blind + retire, Run.)*
>
> I guarded three qubits, my T gates broke two of the checks, so I told the game to ignore those checks. The fidelity is now lower than if I had never posted a sentinel at all. By the end of this video you will know why.

## 0:40 to 1:40 · The problem and where we sit (A, slides 2 and 3)

> The challenge asks how to get more students into quantum error correction, with a game built on one technique: low-overhead error detection with spacetime codes, using qiskit-paulice.
>
> First, where does our game sit? Error detection flags the errors its checks can see and throws those shots away. It repairs nothing. Error mitigation leaves the hardware alone and fixes the estimate afterwards, like ZNE or PEC. Error correction encodes logical qubits and decodes while running. Our game is purely detection. The only currency you have is shots.
>
> A spacetime check is one ancilla that touches one target qubit at a few moments with controlled X, Y or Z gates. Its syndrome, the ancilla bit XOR a few output bits, is deterministic when nothing goes wrong. Spreading the check over time is what makes it hardware friendly.
>
> And the catch: T commutes with Z, but turns X into a mix of X and Y. So a T gate on a wire where a check acts as X or Y breaks that check. On IBM hardware T is a virtual Z rotation, so it costs no noise. It is free for the hardware, but not for the code.

## 1:40 to 3:30 · The game, rule by rule (S, live game + slide 5)

> *(Walk through the screen.)* The board is the spacetime diagram of a six-qubit brickwork Clifford circuit, the same family as the IBM tutorial. Each column is a layer of CZ gates.
>
> Rule one: click a qubit to post a sentinel. That is one ancilla and one check, found by add_pauli_checks with the gamma cost and windowed search. The teal probes show where the check touches its target, and these squares at the readout are the output bits in its syndrome.
>
> Rule two: the level gives a magic quota of T gates. As soon as I post sentinels, every T site turns green or red. Green means every check acts as I or Z there, so a T gate is safe. We read that from qiskit-paulice's uncovered_paulis.
>
> Rule three: choose a placement policy. Safe zones, blind, or blind and retire.
>
> Then Run. Behind this button is an exact Qiskit Aer density-matrix simulation of payload, checks, ancilla readout and post-selection, the four stages shown here. You get the fidelity without checks, the post-selected fidelity, the kept fraction, and the cost: ancillas, extra two-qubit gates and depth.
>
> **Why did we design it this way?** We let qiskit-paulice choose the inside of each check, because hand-drawn checks are almost always invalid and the game would become bookkeeping. The decisions that matter, which qubits to guard and how to place magic, stay with the player. And we kept the bad options legal on purpose, so that players discover with real numbers why they are bad.

## 3:30 to 4:30 · Score and methods (A, slide 6 + notebook)

> The score is the fidelity rate, F post-selected times the kept fraction to the power beta. Why square root? If the leftover error damps an observable by F and you keep kappa of your shots, the error bar of the rescaled estimate goes like one over F root kappa. So R is signal-to-noise per root shot, and one over R squared is the sampling overhead of detection followed by mitigation. Without checks R is just F zero, so beating F zero means your sentinels paid for themselves.
>
> Reference states come from stabilizer simulation for Clifford circuits and statevector for T-doped ones. We use state fidelity because these circuits have flat output distributions: on the deep payload the classical fidelity is 1.000 while the state fidelity is only 0.637. Noise is the challenge's NoiseModel with gate_noise 0.01, used both to pick checks and to simulate, plus a second model from FakeFez calibration data.
>
> We evaluated all 5,412 legal moves, and validated the exact numbers against 50,000-shot runs of the Aer SamplerV2 primitive. The worst deviation is 1.4 standard errors.

## 4:30 to 7:30 · Results: three trade-offs (S then A, slides 7 to 11)

**Finding 1, break-even depth (S).**
> More checks always raise post-selected fidelity and always cost shots. But at depth 6 every check lowers the rate: one check already gives a gain of 0.993, below one, and it gets worse from there. At depth 18 the gain is 1.103: fidelity goes from 0.629 to 0.886 while keeping 0.612 of shots. A check is made of noisy gates. On shallow circuits it mostly catches its own errors.

**Finding 2, T count against check placement (A).**
> With safe-zone placement, fidelity and kept fraction stay flat as we add T gates: the checks see exactly the same faults. With blind placement, checks break and fire on perfect shots. At depth 18 with 16 T gates the post-selected fidelity is 0.892 with safe zones, 0.158 blind, and 0.102 if you retire the broken checks, against 0.628 with no checks at all. Retiring does not help because the ancilla is still entangled with the data. Ignoring it is like measuring and forgetting: it dephases exactly the coherence the T gates create.

**Finding 3, protection and magic compete (S).**
> So why not always place T safely? Because the safe zones shrink. At depth 18 there are 90 T sites; with two checks 29.4 are safe on average, with four 14.3, with six 7.4. A check is useful precisely on the wires where it acts as X or Y, and those are exactly where a T gate would break it. In the game this makes 25 moves illegal, and the best move at depth 18 drops from three checks to q2,q3 when the quota goes to 16 T gates. The right number of checks depends on how much magic you carry.

**Best trade-off (A).**
> For the deep level with four T gates the winner is checks on q0,q3,q4 with safe zones: fidelity 0.632 to 0.910 at 0.615 kept. It wins because its checks overlap little, so they catch most faults, while a fourth check would add more noise than coverage and eat safe sites. And the shot price matters: at beta zero you would use all checks, at beta one none.

## 7:30 to 8:30 · Qiskit and engineering (A, slide 13 + repository)

> Qiskit is everywhere: qiskit-paulice for add_pauli_checks, NoiseModel and from_backend, uncovered_paulis and the post-selection map; quantum_info for stabilizer states and statevectors; Aer for exact density matrices and the SamplerV2 primitive. The repository has a pip-installable package, tests that check the physics, CI, a reproducible notebook, one-command rebuild, and Slurm scripts for HPC.

## 8:30 to 9:30 · Limitations and close (S, slides 14 and 15)

> Honest limitations: six data qubits and at most four checks so every move is exact; uniform noise without idling; the output parity is computed coherently in simulation, which gives the same statistics as the classical XOR; and the web game plays back precomputed Qiskit results, while the terminal version computes live.
>
> The one sentence to remember: protection and magic compete for the same spacetime. Play it at the link below, and thank you.

---

### Checklist before recording
- [ ] `make serve` or the GitHub Pages link opens and the deep level loads.
- [ ] Slides open full screen (`presentation/slides.pdf`).
- [ ] A terminal with `sentinels play --depth 18 --t 4 --targets 0,3,4 --policy safe` ready to show a live Qiskit run (optional, 20 s).
- [ ] Both speakers appear (camera or voice) since both authors contributed equally.
