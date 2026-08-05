#include <stdint.h>
#define MMIO32(address) (*(volatile int32_t *)(address))
#define BNO_ROLL_CD  MMIO32(0x80000060u)
#define BNO_STATUS   MMIO32(0x80000064u)
#define SERVO_R0     MMIO32(0x80000068u)
#define ZERO_BUTTON  MMIO32(0x8000006cu)
#define BNO_PITCH_CD MMIO32(0x80000070u)
#define BNO_YAW_CD   MMIO32(0x80000074u)
#define SERVO_R1     MMIO32(0x80000078u)
#define SERVO_R2     MMIO32(0x8000007cu)

#define STATUS_TIMEOUT 1
#define PWM_MIN_TICKS 13200
#define PWM_CENTER 18000
#define PWM_MAX_TICKS 22800

static int32_t clamp_ticks(int32_t value) {
    if (value < PWM_MIN_TICKS) return PWM_MIN_TICKS;
    if (value > PWM_MAX_TICKS) return PWM_MAX_TICKS;
    return value;
}
static int32_t angle_to_ticks(int32_t angle_cd, int32_t zero_cd) {
    return clamp_ticks(PWM_CENTER - (angle_cd - zero_cd));
}
int main(void) {
    int32_t zero_roll = 0, zero_pitch = 0, zero_yaw = 0;
    int32_t previous_sequence = -1;
    int32_t previous_button = ZERO_BUTTON & 1;
    SERVO_R0 = PWM_CENTER; SERVO_R1 = PWM_CENTER; SERVO_R2 = PWM_CENTER;
    while (1) {
        int32_t status = BNO_STATUS;
        int32_t button = ZERO_BUTTON & 1;
        if (status & STATUS_TIMEOUT) {
            SERVO_R0 = PWM_CENTER; SERVO_R1 = PWM_CENTER; SERVO_R2 = PWM_CENTER;
            continue;
        }
        int32_t sequence = (status >> 8) & 0xff;
        if (sequence != previous_sequence) {
            int32_t roll_cd, pitch_cd, yaw_cd;
            previous_sequence = sequence;
            roll_cd = BNO_ROLL_CD; pitch_cd = BNO_PITCH_CD; yaw_cd = BNO_YAW_CD;
            if (button != previous_button) {
                zero_roll = roll_cd; zero_pitch = pitch_cd; zero_yaw = yaw_cd;
            }
            previous_button = button;
            SERVO_R0 = angle_to_ticks(roll_cd, zero_roll);
            SERVO_R1 = angle_to_ticks(pitch_cd, zero_pitch);
            SERVO_R2 = angle_to_ticks(yaw_cd, zero_yaw);
        }
    }
}
