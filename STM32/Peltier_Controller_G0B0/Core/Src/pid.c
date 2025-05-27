#include <stdlib.h>
#include <string.h>
#include "pid.h"

// Temp points (realtive to room temperature) where we'll estimate PID integral part values
static int Integral_Temp_Table[] = {-15,-10,-5,0,5,10,15,20,25,30,35,40};
// These values have not been found experimentally but rather are assigned logically and roughly making asssumptionns
static double Integral_Part_Table[] = {-12,-8,-4,0,1.5,3,4.5,6,7.5,9,10.5,12};

double compute_pid_output(double current_temp, double set_temp, double outside_temp, double *Kp_part, double *Ki_part, double *Kd_part){
	static int integral_on = 0;
	static double integral = 0;
	static double previous_error[Number_Of_points_For_Kd_calc] = {0};
	static double previous_set_temp = 0;
	static int points_collected_since_set_temp_reset = 0;
	static double integral_estimate = 0;
	double error = 0;

	if(set_temp != previous_set_temp){
		memset(previous_error, 0, Number_Of_points_For_Kd_calc*sizeof(double));
		points_collected_since_set_temp_reset = 0;
		integral_on = 0;
		integral = 0;
	}

	previous_set_temp = set_temp;
	error = set_temp - current_temp;

	if( (abs(current_temp - set_temp) / set_temp) <= 1 - Ki_introduction_point && integral_on == 0){
		integral_estimate = assign_integral_value(set_temp, outside_temp);
		integral = integral_estimate;
		integral_on = 1;
	}

	if(integral_on && abs(Ki*integral_estimate - (Ki*(integral + error * dT))) <= Integral_max_deviation ){
		integral += error * dT;
	}

	(*Kp_part) = Kp * error;
	(*Ki_part) = Ki * integral;
	(*Kd_part) = Kd * compute_derivative_part(error, previous_error, points_collected_since_set_temp_reset);
	points_collected_since_set_temp_reset++;

	return (*Kp_part) + (*Ki_part) + (*Kd_part);
}

double assign_integral_value(double set_temp, double outside_temp){
	double temp_diff = set_temp - outside_temp;
	double previous_closeness = 999;
	for(int i = 0; i < 12; i++){
		if (abs(temp_diff - Integral_Temp_Table[i]) < previous_closeness){
			previous_closeness = abs(temp_diff - Integral_Temp_Table[i]);
		}
		else{
			return Integral_Part_Table[i-1] / Ki;
		}
	}
	return 0;
}

double compute_derivative_part(double current_error, double *error_history, int points_collected_since_set_temp_reset){
	double avg_speed = 0;

	// Push every element to the left and add to the right
	for(int i = 0; i < Number_Of_points_For_Kd_calc -1; i++){
		error_history[i] = error_history[i+1];
	}
	error_history[Number_Of_points_For_Kd_calc-1] = current_error;

	// Calc the avg speed
	double earliest_error = 0;
	if (points_collected_since_set_temp_reset < Number_Of_points_For_Kd_calc){
		earliest_error = error_history[Number_Of_points_For_Kd_calc - 1 - points_collected_since_set_temp_reset];
	}
	else{
		earliest_error = error_history[0];
	}
	avg_speed = (error_history[Number_Of_points_For_Kd_calc-1] - earliest_error) / (Number_Of_points_For_Kd_calc*dT);
	return avg_speed;
}


