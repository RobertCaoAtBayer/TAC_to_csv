"""
Shamelessly copy from SY2-SQA-TAF/MCU_Test_Automation/MCUDefines.py
"""
from enum import IntEnum, auto


class BaseEnum(IntEnum):
    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return f"{self.value} {self.name}"


class Alarms(BaseEnum):
    """
    Alarm bitmap indexes
    The order here must match the DIGEST response alarm code order
    The collection of related strings DIGEST_ALARMS must also be in the same order

    Corresponds to ST2CLI alarms
    """

    ALARM_POST_BAD_SYSTEM_CRC = 0
    ALARM_POST_WATCH_DOG_RESET = auto()
    ALARM_POST_LOW_POWER_RESET = auto()
    ALARM_POST_12V_LEVEL_CHECK_FAILED = auto()
    ALARM_POST_5V_LEVEL_CHECK_FAILED = auto()
    ALARM_POST_36V_LEVEL_CHECK_FAILED = auto()
    ALARM_POST_SC_VERSION_MISMATCH = auto()
    ALARM_POST_STOP_BTN_PRESSED = auto()
    ALARM_POST_ADVANCE_BTN_PRESSED = auto()
    ALARM_POST_MCU_SC_CLOCK_CHK_FAIL = auto()
    ALARM_POST_LED_VOLTAGE_CHECK_FAILED = auto()

    ALARM_HCU_SHUTDOWN_FAILED = auto()
    ALARM_STOP_BTN_FAULT = auto()
    ALARM_VMT_OUT_RANGE = auto()
    ALARM_BASE_OVER_TEMPERATURE = auto()  # new

    # ALARM_PRESSURE_METER_CAL_NEEDED = 14
    ALARM_PRESSURE_CAL_NEEDED_S0 = auto()
    ALARM_PRESSURE_CAL_NEEDED_C1 = auto()
    ALARM_PRESSURE_CAL_NEEDED_C2 = auto()

    ALARM_MOTOR_PLUNGER_CAL_NEEDED_S0 = auto()
    ALARM_MOTOR_CAL_NEEDED_S0 = auto()
    ALARM_MOTOR_HALL_SENSOR_OUT_RANGE_S0 = auto()
    ALARM_MOTOR_ZERO_VOLUME_NOT_SET_S0 = auto()
    ALARM_MOTOR_ELECTRICAL_FAULT_S0 = auto()
    ALARM_MOTOR_FINAL_DRIVE_ENCODER_FAULT_S0 = auto()
    ALARM_MOTOR_HOME_SENSOR_FAULT_S0 = auto()

    ALARM_MOTOR_PLUNGER_CAL_NEEDED_C1 = auto()
    ALARM_MOTOR_CAL_NEEDED_C1 = auto()
    ALARM_MOTOR_HALL_SENSOR_OUT_RANGE_C1 = auto()
    ALARM_MOTOR_ZERO_VOLUME_NOT_SET_C1 = auto()
    ALARM_MOTOR_ELECTRICAL_FAULT_C1 = auto()
    ALARM_MOTOR_FINAL_DRIVE_ENCODER_FAULT_C1 = auto()
    ALARM_MOTOR_HOME_SENSOR_FAULT_C1 = auto()

    ALARM_MOTOR_PLUNGER_CAL_NEEDED_C2 = auto()
    ALARM_MOTOR_CAL_NEEDED_C2 = auto()
    ALARM_MOTOR_HALL_SENSOR_OUT_RANGE_C2 = auto()
    ALARM_MOTOR_ZERO_VOLUME_NOT_SET_C2 = auto()
    ALARM_MOTOR_ELECTRICAL_FAULT_C2 = auto()
    ALARM_MOTOR_FINAL_DRIVE_ENCODER_FAULT_C2 = auto()
    ALARM_MOTOR_HOME_SENSOR_FAULT_C2 = auto()

    ALARM_MOTOR_LOST_POSITION_S0 = auto()
    ALARM_MOTOR_LOST_POSITION_C1 = auto()
    ALARM_MOTOR_LOST_POSITION_C2 = auto()

    ALARM_INLET_AIR_CAL_NEEDED_S0 = auto()
    ALARM_INLET_AIR_SENSOR_FAULT_S0 = auto()

    ALARM_INLET_AIR_CAL_NEEDED_C1 = auto()
    ALARM_INLET_AIR_SENSOR_FAULT_C1 = auto()

    ALARM_INLET_AIR_CAL_NEEDED_C2 = auto()
    ALARM_INLET_AIR_SENSOR_FAULT_C2 = auto()

    ALARM_SUDS_CAL_NEEDED = auto()
    ALARM_SUDS_SENSOR_FAULT = auto()

    ALARM_OUTLET_AIR_SENSOR_FAULT = auto()

    ALARM_DOOR_MECHANISM_FAILED = auto()
    ALARM_DOOR_OPEN_FAULT = auto()

    ALARM_SC_WATCH_DOG_RESET = auto()
    ALARM_SC_CRC_FAULT = auto()
    ALARM_SC_ENGAGEMENT_FAULT_S0 = auto()
    ALARM_SC_ENGAGEMENT_FAULT_C1 = auto()
    ALARM_SC_ENGAGEMENT_FAULT_C2 = auto()

    ALARM_SC_HBRIDGE_FAULT_S0 = auto()
    ALARM_SC_HBRIDGE_FAULT_C1 = auto()
    ALARM_SC_HBRIDGE_FAULT_C2 = auto()

    ALARM_SC_ENCODER_FAULT_S0 = auto()
    ALARM_SC_ENCODER_FAULT_C1 = auto()
    ALARM_SC_ENCODER_FAULT_C2 = auto()

    ALARM_SC_TIMEOUT_FAULT_S0 = auto()
    ALARM_SC_TIMEOUT_FAULT_C1 = auto()
    ALARM_SC_TIMEOUT_FAULT_C2 = auto()

    ALARM_SC_UNINTENDED_MOTION_DETECTED_S0 = auto()
    ALARM_SC_UNINTENDED_MOTION_DETECTED_C1 = auto()
    ALARM_SC_UNINTENDED_MOTION_DETECTED_C2 = auto()

    ALARM_I2C_MOTOR_MUX_FAULT = auto()
    ALARM_I2C_SC_FAULT = auto()

    ALARM_I2C_MOTOR_ADC_FAULT_S0 = auto()
    ALARM_I2C_MOTOR_IO_FAULT_S0 = auto()
    ALARM_I2C_MOTOR_FRAM_FAULT_S0 = auto()
    ALARM_I2C_MOTOR_BAD_ADDRESS_S0 = auto()

    ALARM_I2C_MOTOR_ADC_FAULT_C1 = auto()
    ALARM_I2C_MOTOR_IO_FAULT_C1 = auto()
    ALARM_I2C_MOTOR_FRAM_FAULT_C1 = auto()
    ALARM_I2C_MOTOR_BAD_ADDRESS_C1 = auto()

    ALARM_I2C_MOTOR_ADC_FAULT_C2 = auto()
    ALARM_I2C_MOTOR_IO_FAULT_C2 = auto()
    ALARM_I2C_MOTOR_FRAM_FAULT_C2 = auto()
    ALARM_I2C_MOTOR_BAD_ADDRESS_C2 = auto()

    ALARM_I2C_GENERAL_BASE_ADC_FAULT = auto()
    ALARM_I2C_GENERAL_BASE_IO_FAULT = auto()
    ALARM_I2C_GENERAL_BASE_FAN_FAULT = auto()

    ALARM_I2C_GENERAL_BATTERY_MANAGEMENT_SYSTEM_A = auto()
    ALARM_I2C_GENERAL_BATTERY_MANAGEMENT_SYSTEM_B = auto()

    ALARM_I2C_GENERAL_HEAT_MAINTAINER_COMM_FAULT_CORE = auto()
    ALARM_I2C_GENERAL_HEAT_MAINTAINER_COMM_FAULT_DOOR = auto()

    ALARM_I2C_GENERAL_WASTE_CONTAINER_DETECT_COMM_FAULT = auto()
    ALARM_I2C_GENERAL_WASTE_CONTAINER_LEVEL_COMM_FAULT = auto()

    ALARM_I2C_GENERAL_INLET_AIR_DETECT_COMM_FAULT_S0 = auto()
    ALARM_I2C_GENERAL_INLET_AIR_DETECT_COMM_FAULT_C1 = auto()
    ALARM_I2C_GENERAL_INLET_AIR_DETECT_COMM_FAULT_C2 = auto()

    ALARM_I2C_GENERAL_SUDS_COMM_FAULT = auto()
    ALARM_I2C_GENERAL_DOOR_LOCK_COMM_FAULT = auto()

    ALARM_I2C_GENERAL_LED_SUDS_COMM_FAULT = auto()
    ALARM_I2C_GENERAL_LED_DOOR_COMM_FAULT = auto()
    ALARM_I2C_GENERAL_LED_TOP_COMM_FAULT = auto()

    ALARM_I2C_GENERAL_MUX_FAULT = auto()
    ALARM_I2C_GENERAL_BAD_ADDRESS = auto()

    ALARM_HEAT_MAINTAINER_POWER_FAULT_CORE = auto()
    ALARM_HEAT_MAINTAINER_POWER_FAULT_DOOR = auto()
    ALARM_HEAT_MAINTAINER_DIGITAL_POWER_FAULT_CORE = auto()
    ALARM_HEAT_MAINTAINER_DIGITAL_POWER_FAULT_DOOR = auto()

    ALARM_I2C_MOTOR_PLUNGER_POT_FAULT_S0 = auto()
    ALARM_I2C_MOTOR_PLUNGER_POT_FAULT_C1 = auto()
    ALARM_I2C_MOTOR_PLUNGER_POT_FAULT_C2 = auto()
    
    ALARM_I2C_MOTOR_LOCK_UNLOCK_POT_FAULT_S0 = auto()
    ALARM_I2C_MOTOR_LOCK_UNLOCK_POT_FAULT_C1 = auto()
    ALARM_I2C_MOTOR_LOCK_UNLOCK_POT_FAULT_C2 = auto()
    
    ALARM_MOTOR_UNEXPECTED_PLUNGER_TRANSITION_S0 = auto()
    ALARM_MOTOR_UNEXPECTED_PLUNGER_TRANSITION_C1 = auto()
    ALARM_MOTOR_UNEXPECTED_PLUNGER_TRANSITION_C2 = auto()
    ALARM_COUNT = auto()

    @staticmethod
    def get_alarm_list(alarm_str):
        """
        Get the alarm bitmap, interpret it and return a list of active alarms IDs
        :param alarm_str: Alarm bitmap from Digest response
        :return: List of active alarm IDs
        """
        alarm_list = []

        # Split into byte strings and convert to bytes
        bytes_stream = [int(alarm_str[ix:ix + 2], 16) for ix in range(0, len(alarm_str), 2)]
        bytes_stream.reverse()
        bytes_len = len(bytes_stream)
        for ix in range(bytes_len):
            for jx in range(8):
                if bytes_stream[ix] & 0x01:
                    alarm_num = ix * 8 + jx
                    alarm_list.append(alarm_num)
                bytes_stream[ix] >>= 1

        return alarm_list

    @staticmethod
    def get_alarm_names(alarm_str):
        """
        Get the list of active alarms and convert into a list of alarm names
        :param alarm_str: Alarm bitmap from Digest response
        :return: List of alarm names
        """
        try:
            alarm_list = Alarms.get_alarm_list(alarm_str)
        except ValueError:
            print("invalid alarm string", alarm_str)
            return []
        # return alarm name with ID
        return list(str(Alarms(alarm_id)) for alarm_id in alarm_list)


if __name__ == '__main__':
    print("All possible alarms")
    # xxx = "4000000000000000000000"
    # xxx = "080000000000000000000000"
    # xxx = "040D0E0444800002000000038243"
    # xxx = '040D1E000080000A000000000243'
    xxx = '010000000000000000000000'
    for val in Alarms.get_alarm_names(xxx):
        print("    ", val)
