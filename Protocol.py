import random


class Protocol:
    types = {"SALINE", "CONTRAST1", "CONTRAST2", "DUAL1", "DUAL2", "NONE", "PAUSE"}

    def __init__(self, prime_type="SALINE", pressure=2068, flow_reduction=45, pressure_limit_sensitivity=75):
        self._phases = []
        self._prime_type = prime_type
        self._pressure = pressure
        self._flow_reduction = flow_reduction
        self._pressure_limit_sensitivity = pressure_limit_sensitivity

    def __str__(self):
        # "">ARM@2068,3,SALINE,43,75,"
        arm_prefix = ">ARM@%d,%d,%s,%d,%d" % \
                     (self._pressure, len(self._phases), self._prime_type,
                      self._flow_reduction, self._pressure_limit_sensitivity)
        # "DUAL2,50,19.0,10.0,0"
        phases = ["%s,%d,%.01f,%.01f,%d" % tuple(x) for x in self._phases]
        return ",".join([arm_prefix] + phases)

    def count(self):
        return len(self._phases)

    def add_phase(self, phase_type: str, volume, flow, mix, pause=0):
        if phase_type not in self.types:
            print("ERROR invalid phase type", phase_type)
            exit(1)
        if volume > 200:
            # print("ERROR invalid volume ", volume)
            # exit(1)
            print("WARNING: allow for >200ml phase volume (must be a dual flow!)")
            pass
        if flow > 10:
            print("ERROR invalid flow rate", flow)
            exit(1)
        if mix > 100 or mix < 0:
            print("ERROR invalid mix ", mix)
            exit(1)

        self._phases.append((phase_type, mix, volume, flow, pause))

    def get_durations_in_ms(self) -> int:
        total_time_ms = 0
        for phase_type, mix, volume, flow, pause in self._phases:
            if phase_type in ["SALINE", "CONTRAST1", "CONTRAST2", "DUAL1", "DUAL2"]:
                total_time_ms += int(volume / flow * 1000) + pause
            else:
                # NONE or PAUSE
                total_time_ms += pause
        return total_time_ms

    def get_phase_durations_in_ms(self) -> list:
        ret = []
        for phase_type, mix, volume, flow, pause in self._phases:
            if phase_type in ["SALINE", "CONTRAST1", "CONTRAST2", "DUAL1", "DUAL2"]:
                ret.append(int(volume / flow * 1000) + pause)
            else:
                # NONE or PAUSE
                ret.append(pause)
        return ret

    def enough_volumes(self, max_vol) -> bool:
        for v in self.get_volumes():
            if v > max_vol:
                return False
        return True

    def get_phase_volumes(self, phase_index):
        vol = [0.0, 0.0, 0.0]
        phase_type, mix, volume, flow, pause = self._phases[phase_index]
        if phase_type == "SALINE":
            vol[0] += volume
        elif phase_type == "CONTRAST1":
            vol[1] += volume
        elif phase_type == "CONTRAST2":
            vol[2] += volume
        elif phase_type == "DUAL1":
            vol[0] += (volume * (100 - mix) / 100)
            vol[1] += (volume * mix / 100)
        elif phase_type == "DUAL2":
            vol[0] += (volume * (100 - mix) / 100)
            vol[2] += (volume * mix / 100)
        return vol

    def get_volumes(self):
        all_vol = [0.0, 0.0, 0.0]
        for i in range(len(self._phases)):
            vol = self.get_phase_volumes(i)
            for j in range(len(vol)):   # can be optimised!
                all_vol[j] += vol[j]
        return all_vol

    @staticmethod
    def from_string(arm_str):
        arm_str = arm_str.strip()
        arm_str = ",".join(arm_str.split("@"))
        arm_str = ",".join(arm_str.split(" "))
        arr = list(filter(None, arm_str.split(",")))    # filter to remove consecutive escape chars e.g. "@ "
        # ">ARM@2068,3,SALINE,43,75,CONTRAST2,100,19.0,10.0,0,DUAL2,50,19.0,10.0,0,SALINE,0,19.0,10.0,0"
        pressure = int(arr[1])
        phases = int(arr[2])
        prime_type = arr[3]
        flow_reduction = int(arr[4])
        pressure_limit_sensitivity = int(arr[5])

        if len(arr) != (6 + phases * 5):
            print("Invalid protocol")
            return None

        protocol = Protocol(prime_type, pressure, flow_reduction, pressure_limit_sensitivity)
        for i in range(phases):
            idx = 6 + i * 5
            phase_type = arr[idx + 0]
            mix = int(arr[idx + 1])
            volume = float(arr[idx + 2])
            flow = float(arr[idx + 3])
            pause = int(arr[idx + 4])
            protocol.add_phase(phase_type, volume, flow, mix, pause)
        return protocol

    def get_phases(self):
        return self._phases

    @staticmethod
    def load_protocols_from_file(filename) -> dict:
        """
        Loading ARM commands from the given text file.
        Return a dictionary where
            key is protocol integer index
            value is Protocol
        """
        protocols = dict()
        with open(filename) as fh:
            index = 0
            for line in fh:
                org_line = line = line.strip()
                index += 1
                if len(line):
                    if '#' == line[0]:
                        continue  # skip comment
                    line = line.split("#")[0]  # strip comments
                    if len(line):
                        protocol = Protocol.from_string(line)
                        if protocol is None:
                            print("Skip line %d due to protocol error '%s'" % (index, org_line))
                        else:
                            protocols[index] = protocol
        return protocols


def gen_3_phases(filename):
    print("Generate", filename)
    # volumes = list(range(1, 10, 1)) + list(range(10, 101, 15))
    # volumes = [5, 10, 30, 50, 80, 100]
    volumes = [10, 50]
    print("volume", len(volumes), volumes)
    # flow_rates = [0.1, 0.5, 0.8] + list(range(1, 11))
    flow_rates = [1, 8]
    print("flow_rates", len(flow_rates), flow_rates)

    # mixes = list(range(5, 96, 5))  # [5,95]
    mixes = list(range(30, 96, 30))  # [5,95]
    print("mix", len(mixes), mixes)

    phases = []
    # single phase
    fh = open(filename, "w")
    for phase in ["SALINE", "CONTRAST1", "CONTRAST2"]:
        for volume in volumes:
            for flow_rate in flow_rates:
                p = Protocol()
                p.add_phase(phase, volume=volume, flow=flow_rate, mix=100, pause=0)
                fh.write(str(p) + "\n")
                phases.append((phase, volume, flow_rate, 100, 0))
    for phase in ["DUAL1", "DUAL2"]:
        for volume in volumes:
            for flow_rate in flow_rates:
                for mix in mixes:
                    p = Protocol()
                    p.add_phase(phase, volume=volume, flow=flow_rate, mix=mix, pause=0)
                    fh.write(str(p) + "\n")
                    phases.append((phase, volume, flow_rate, mix, 0))

    lines = set()
    while len(lines) < 200:
        p = Protocol()
        for j in range(random.randint(3, 3)):
            idx = random.randint(0, len(phases)-1)
            phase, volume, flow_rate, mix, pause = phases[idx]
            phases.append((phase, volume, flow_rate, mix, 0))
            p.add_phase(phase, volume, flow_rate, mix, pause)
        lines.add(str(p))
        # todo need to check if there is not enough permutation to break the loop.

    for line in lines:
        fh.write(line + "\n")
    fh.close()


def generate_random_phases(filename):
    print("Generate", filename)
    # volumes = list(range(1, 10, 1)) + list(range(10, 101, 15))
    volumes = [5, 10, 30, 50, 80, 100]
    print("volume", len(volumes), volumes)
    # flow_rates = [0.1, 0.5, 0.8] + list(range(1, 11))
    flow_rates = [1, 2, 5, 8, 10]
    print("flow_rates", len(flow_rates), flow_rates)

    # mixes = list(range(5, 96, 5))  # [5,95]
    mixes = list(range(30, 96, 15))  # [5,95]
    print("mix", len(mixes), mixes)

    phases = []
    # single phase
    fh = open(filename, "w")
    for phase in ["SALINE", "CONTRAST1", "CONTRAST2"]:
        for volume in volumes:
            for flow_rate in flow_rates:
                p = Protocol()
                p.add_phase(phase, volume=volume, flow=flow_rate, mix=100, pause=0)
                fh.write(str(p) + "\n")
                phases.append((phase, volume, flow_rate, 100, 0))
    for phase in ["DUAL1", "DUAL2"]:
        for volume in volumes:
            for flow_rate in flow_rates:
                for mix in mixes:
                    p = Protocol()
                    p.add_phase(phase, volume=volume, flow=flow_rate, mix=mix, pause=0)
                    fh.write(str(p) + "\n")
                    phases.append((phase, volume, flow_rate, mix, 0))

    for i in range(200):
        p = Protocol()
        for j in range(random.randint(2, 6)):
            idx = random.randint(0, len(phases)-1)
            phase, volume, flow_rate, mix, pause = phases[idx]
            phases.append((phase, volume, flow_rate, mix, 0))
            p.add_phase(phase, volume, flow_rate, mix, pause)
        fh.write(str(p) + "\n")
    fh.close()


# noinspection PyPep8Naming
def generate_JESRA(filename):
    flow_vols = [
        (0.1, 1),
        (0.1, 100),
        (0.1, 200),
        (5, 1),
        (5, 100),
        (5, 200),
        (10, 1),
        (10, 100),
        (10, 200)
    ]
    fh = open(filename, "w")
    for phase in ["SALINE", "CONTRAST1", "CONTRAST2"]:
        for flow_rate, volume in flow_vols:
            p = Protocol()
            p.add_phase(phase, volume=volume, flow=flow_rate, mix=100, pause=0)
            fh.write(str(p) + "\n")
    fh.close()


def generate_3_phases(filename, phase_volume=80, flow_rate=5):
    phases_mixes = [("SALINE", 0),
                    ("CONTRAST1", 100),
                    ("CONTRAST2", 100),
                    ('DUAL1', 10),
                    # ('DUAL1', 50),
                    ('DUAL1', 90),
                    # ('DUAL2', 10),
                    # ('DUAL2', 50),
                    # ('DUAL2', 50)
                    ]
    with open(filename, "w") as fh:
        for phase1, mix1, in phases_mixes:
            for phase2, mix2, in phases_mixes:
                for phase3, mix3, in phases_mixes:
                    if (phase1, mix1) == (phase2, mix2):  # skip the same adjacent
                        continue
                    if (phase3, mix3) == (phase2, mix2):
                        continue
                    if phase1 == "CONTRAST1" and (phase2 in ['DUAL2', 'CONTRAST2']) and (phase3 in ['DUAL1', 'CONTRAST1']):
                        continue
                    if phase1 == "CONTRAST2" and (phase2 in ['DUAL1', 'CONTRAST1']) and (phase3 in ['DUAL2', 'CONTRAST2']):
                        continue
                    if phase1 == 'DUAL2' and (phase2 in ['DUAL1', 'CONTRAST1']) and (phase3 in ['DUAL2', 'CONTRAST2']):
                        continue
                    if phase1 == 'DUAL1' and (phase2 in ['DUAL2', 'CONTRAST2']) and (phase3 in ['DUAL1', 'CONTRAST1']):
                        continue

                    p = Protocol()
                    p.add_phase(phase1, volume=phase_volume, flow=flow_rate, mix=mix1, pause=0)
                    p.add_phase(phase2, volume=phase_volume, flow=flow_rate, mix=mix2, pause=0)
                    p.add_phase(phase3, volume=phase_volume, flow=flow_rate, mix=mix3, pause=0)
                    if p.enough_volumes(max_vol=200):
                        fh.write(str(p) + "\n")
                    else:
                        print("Skip due to not enough volume", p.get_volumes(), str(p))


def test1():
    p = Protocol()
    p.add_phase(phase_type="SALINE", volume=5, flow=5, mix=100, pause=0)
    p.add_phase(phase_type="CONTRAST1", volume=5, flow=5, mix=100, pause=0)

    p_str = ">ARM@2068,3,SALINE,43,75,CONTRAST2,100,19.0,10.0,0,DUAL2,50,19.0,10.0,0,SALINE,0,19.0,10.0,0"
    p2 = Protocol.from_string(p_str)
    print(p2)
    print(p_str)
    assert str(p2) == p_str


if __name__ == '__main__':
    # generate_random_phases("random_phases.txt")
    # generate_JESRA("JESRA.txt")
    # Protocol.load_protocols_from_file("JESRA.txt")
    generate_3_phases("protocol_3phases_gen_10mlps.txt", phase_volume=60, flow_rate=10)
    print("done")
