
class Command:
    def __init__(self, cmd):
        self._cmd: str = cmd
        self.response = None

    def get_command(self):
        return self._cmd

    def get_name(self):
        for val in "@ ,\t":
            idx = self._cmd.find(val)
            if idx != -1:
                return self._cmd[:idx]
        return self._cmd.split("\r")[0]

    def parse_response(self, response_string):
        return response_string


class InfoCommand(Command):
    def __init__(self):
        super(self.__class__, self).__init__(">info")
    
    def parse_response(self, response_string):
        arr = response_string.split(",")
        # # >info#
        # Stl2CLI,
        # 0,0,43,11, # up time in date hour, minute, second
        # POR,
        # DAVID'S MCU,
        # 13000102,
        # COMM_FAILED,
        # COMM_FAILED
        if len(arr) == 10:
            return {"NAME": arr[0],
                    "UP_TIME": [int(x) for x in arr[1:5]],
                    "RESET_REASON": arr[5],
                    "CLI_VERSION": arr[3],
                    "MCU_SERIAL": arr[-4],
                    "MOTOR_SERIALS": arr[-3:]}
        else:
            return {"DATA": arr}


class VersionCommand(Command):
    def __init__(self):
        super(self.__class__, self).__init__(">version")

    def parse_response(self, response_string):
        arr = response_string.split(",")
        if len(arr) == 3:
            return {"MCU": arr[0], "Stopcock": arr[1], "CLI": arr[2]}
        else:
            return {"MCU": response_string, "Stopcock": "Unknown", "CLI": "Unknown"}


class DigestCommand(Command):
    header = [
            "alarmcode",
            "injector_state",
            "inject_complete_reason",
            "pressure",
            "sc1",
            "sc2",
            "sc3",
            "plng1",
            "plng2",
            "plng3",
            "syract1",
            "syract2",
            "syract3",
            "vol1",
            "vol2",
            "vol3",
            "flow1",
            "flow2",
            "flow3",
            "battery_level",
            "ac_powered",
            "door",
            "wastebin",
            "muds_present",
            "muds_latch",
            "inbubble1",
            "inbubble2",
            "inbubble3",
            "suds",
            "sudsbubble",
            "primebtn",
            "stopbtn",
            "doorbtn",
            "outlet_door_state",
            "heater1_temperature",
            "heater2_temperature",
            "heater_state",
            "shutdown_state",
            "diagnostic",       # CLI 43
            "mcu_log_message"
        ]

    def __init__(self):
        super(self.__class__, self).__init__(">digest")

    def parse_response(self, response_string):
        arr = response_string.split(",")
        self.response = arr     # any one else done it?
        return arr  # todo conversion to dictionary


AF_map = {'AF_OFF': 0, 'AF_ACTIVE': 1, 'AF_CRITICAL': 2}
Stopcock_id_to_name = ('SC_CLOSED', 'SC_MOVING', 'SC_FILL', 'SC_INJECT', 'SC_UNKNOWN')
Stopcock_map = {v: i for i, v in enumerate(Stopcock_id_to_name)}


class InjectDigestCommand(Command):
    header = [
        "phase",
        "adaptive_flow",
        "scheduled_pulsing_active",
        "unscheduled_pulsing_active",
        "injection_pressure",
        "saline_pressure",
        "contrast1_pressure",
        "contrast2_pressure",
        "saline_PID",
        "contrast1_PID",
        "contrast2_PID",
        "saline_SC_position",
        "contrast1_SC_position",
        "contrast2_SC_position",
        "saline_motor_position",
        "contrast1_motor_position",
        "contrast2_motor_position",
        "saline_ss_reduction",
        "contrast1_ss_reduction",
        "contrast2_ss_reduction",
        "saline_stored_compliance",
        "contrast1_stored_compliance",
        "contrast2_stored_compliance",
        "saline_phase_compliance",
        "contrast1_phase_compliance",
        "contrast2_phase_compliance",
        "patient_line_aircounts",
        "Pressure_adc",                 # "pin_120",
        "dP",                           # "pin_121",
        "patient_line_air_volume_ul",   #  'INJECT_PRESSURE' aka "pin_122",
        "max_pressure",                 # "3mm_port",
        "saline_flowrate_phase",
        "contrast1_flow_rate_phase",
        "contrast2_flow_rate_phase",
        "saline_vol_pushed",
        "contrast1_vol_pushed",
        "contrast2_vol_pushed",
        "saline_vol_delivered_phase_i",
        "contrast1_vol_delivered_phase_i",
        "contrast2_vol_delivered_phase_i",
        "duration_phase_i"
    ]

    def __init__(self, delay_ms=0):
        command = ">injectdigest" if delay_ms == 0 else ">injectdigest %d" % delay_ms
        super(self.__class__, self).__init__(command)

    def parse_response(self, response_string, verbose=True):
        if verbose:
            print(response_string)
        arr = response_string.split(",")
        if len(arr) > len(self.header):
            # @todo need to ensure if the previous time of the 2nd last digest is not the
            #  as the last know time then insert the last on in.
            # ensure the array as 41 field
            arr = arr[:len(self.header) - 4] + arr[-4:]
        if len(arr) != len(self.header):
            return []
        # for i, v in enumerate(arr):
        #    print(i, v, self.header[i])
        arr[1] = AF_map[arr[1]]    # adaptive flow translation to int
        arr[11] = Stopcock_map[arr[11]]
        arr[12] = Stopcock_map[arr[12]]
        arr[13] = Stopcock_map[arr[13]]

        res = []
        for i, x in enumerate(arr):
            # noinspection PyBroadException
            try:
                v = float(x)
                res.append(v)
            except:
                v = int(x.split(".")[0])
                #  @todo mcu to fix this
                print("***Invalid number %s -> %s field %d %s" % (x, v, i, self.header[i]))
                """
                Invalid number -47.-9 -> -47 field 34 saline_vol_pushed
                Invalid number -112.-7 -> -112 field 35 contrast1_vol_pushed
                Invalid number -26.-6 -> -26 field 36 contrast2_vol_pushed
                """
                res.append(v)      # todo mcu to fix it
        return arr  # todo conversion to dictionary


class MotorDigestCommand(Command):
    header = [
        "msTimeStamp",
        "phase",
        "Saline speed",
        "Saline OAD speed",
        "Saline PID error",
        "Saline PID",
        "Saline position",
        "Saline Stopcock",
        "C1 speed",
        "C1 OAD speed",
        "C1 PID error",
        "C1 PID",
        "C1 position",
        "C1 Stopcock",
        "C2 speed",
        "C2 OAD speed",
        "C2 PID error",
        "C2 PID",
        "C2 position",
        "C2 Stopcock",
        "Saline Pressure",
        "C1 Pressure",
        "C2 Pressure",
        "Inject pressure",
        "PressureMeter",
        "PBVolume",
        "ADC_Pin120",
        "ADC_Pin121",
        "ADC_Pin122"
    ]

    def __init__(self):
        super(self.__class__, self).__init__(">motordigest")

    def parse_response(self, response_string):
        arr = response_string.split(",")
        self.response = arr     # any one else done it?
        return arr  # todo conversion to dictionary
