# Uputstvo za pokretanje projekta

Ovaj dokument sadrži detaljne instrukcije za pokretanje projekta sa sva tri testna primjera.

---

## 1. Pokretanje programa

Program se pokreće iz korijenskog (root) direktorijuma projekta i prima **jedan obavezan argument**: lokaciju (putanju) do ulaznog fajla.

Sintaksa:
```bash
python -m src.engine_SimulationEngine <putanja_do_ulaznog_fajla>
```

---

## 2. Primjeri pokretanja za sva tri ulazna scenarija

### Primjer 1: Test scenario bez konflikata (`01_no_conflict`)
```bash
python -m src.engine_SimulationEngine input/01_no_conflict/specs.json
```

### Primjer 2: Test scenario preotimanja resursa (`02_preemption`)
```bash
python -m src.engine_SimulationEngine input/02_preemption/specs.json
```

### Primjer 3: Test scenario pokušaja zastoja (`03_deadlock_attempt`)
```bash
python -m src.engine_SimulationEngine input/03_deadlock_attempt/specs.json
```

---

## 3. Napomene za Windows korisnike
Na Windows operativnom sistemu umjesto obične kose crte (`/`) možete koristiti i obrnutu kosu crtu (`\`):

```cmd
python main.py input\01_no_conflict\ulaz.txt
python main.py input\02_preemption\ulaz.txt
python main.py input\03_deadlock_attempt\ulaz.txt
```
