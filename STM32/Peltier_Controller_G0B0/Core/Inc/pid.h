#ifndef __PID_H
#define __PID_H

#define Kp 4.5
#define Ti 100
#define Kd 550
#define Td 47
#define Ki 0.01
#define dT 1 // seconds
#define integral_cap 10.5
#define Number_Of_points_For_Kd_calc 50
#define Ki_introduction_point 0.90
// limit that defines how close to the setpoint the integral should be introduced
#define Integral_max_deviation 2

double compute_pid_output(double current_temp, double set_temp, double outside_temp, double *Kp_part, double *Ki_part, double *Kd_part);
double compute_derivative_part(double current_error, double *error_history, int points_collected_since_set_temp_reset);
double assign_integral_value(double set_temp, double outside_temp);

#endif
