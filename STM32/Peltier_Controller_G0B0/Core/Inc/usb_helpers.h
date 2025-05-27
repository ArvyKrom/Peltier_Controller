#ifndef __USB_HELPERS_H
#define __USB_HELPERS_H

#include <stdint.h>

void send_temps_via_usb(double current_temp_inside, double current_temp_outside);
void listen_for_temp_change_sent_via_usb(double *set_temp_inside);
int string_to_double(uint8_t *data, uint8_t size, double *result);
int put_temps_into_char_array(double temp1, double temp2, uint8_t *char_array, uint8_t size);

#endif
