#ifndef __PID_H
#define __PID_H

#define Kp 10
#define Ki 0.05
#define Kd 500
#define dT 1 // seconds
#define integral_cap 50

double compute_pid_output(double error);
double compute_derivative_part(double current_error, double *error_history, int size);
int push_new_value_from_the_end(double new_val, double *array, int size);

#endif
