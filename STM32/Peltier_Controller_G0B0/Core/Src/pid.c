#include <stdlib.h>
#include "pid.h"

double compute_pid_output(double error){
	static double integral = 0;
	static double previous_error[10] = {0};
	double pid_output = Kp*error + Ki*integral + Kd*compute_derivative_part(error, previous_error, 10);
	push_new_value_from_the_end(error, previous_error, 10);
	if(abs(integral + error * dT) < integral_cap){
		integral += error * dT;
	}
	return pid_output;
}

double compute_derivative_part(double current_error, double *error_history, int size){
	for(int i = 0;i<size;i++){
		if(current_error - error_history[size-1-i] != 0){
			return (current_error - error_history[size-1-i])/(dT*(1+i));
		}
	}
	return 0.0;
}

int push_new_value_from_the_end(double new_val, double *array, int size){
	for(int i = size-2;i>=0; i--){
		array[i] = array[i+1];
	}
	array[size - 1] = new_val;
	return 0;
}
