#include <stdlib.h>
#include <string.h>
#include "usb_helpers.h"
#include "usbd_cdc_if.h"


void send_temps_via_usb(double current_temp_inside, double current_temp_outside){
	uint8_t usb_tx_data[20] = {0};
	put_temps_into_char_array(current_temp_inside, current_temp_outside, usb_tx_data, 20);
	CDC_Transmit_FS(usb_tx_data, 20);
}

void listen_for_temp_change_sent_via_usb(double *set_temp_inside){
	uint32_t len = 20;
	static uint8_t usb_rx_data[20] = {0};
	CDC_Receive(usb_rx_data, &len);

	if(usb_rx_data[0] != '\0' && string_to_double(usb_rx_data, 20, set_temp_inside) != 1){
		memset(usb_rx_data, 0, 20);
	}
}


int string_to_double(uint8_t *data, uint8_t size, double *result){
	char *endptr = NULL;
	double temp = strtod((const char*)data, &endptr);

	if (*endptr != '\0' && *endptr != '\n')
		return 1;

	*result = temp;
	return 0;

}
int put_temps_into_char_array(double temp1, double temp2, uint8_t *char_array, uint8_t size){
	memset(char_array,0, size);
	snprintf((char*)char_array, size, "%.1lf, %.1lf\n", temp1, temp2);
	return 0;
}
