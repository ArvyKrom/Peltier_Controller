#include "main.h"
#include "tmp1075.h"

int read_temp(I2C_HandleTypeDef *hi2c, uint8_t dev_addr, double *temp){
	uint8_t raw_data[2] = {0};
	if(read_reg(hi2c,dev_addr,TEMP_reg_addr,raw_data,2) != 0)
		return 1;
	*temp = ((raw_data[0] << 4) | (raw_data[1]) >> 4) * 0.0625; //0.0625C per LSB
	return 0;
}

int read_reg(I2C_HandleTypeDef *hi2c, uint16_t dev_addr, uint8_t reg_addr, uint8_t *rx_data, uint8_t size){

	if(HAL_I2C_Master_Transmit(hi2c, dev_addr, &reg_addr, 1, 100) != HAL_OK)
		return 1;

	if(HAL_I2C_Master_Receive(hi2c, dev_addr, rx_data, size, 100) != HAL_OK)
		return 1;

	return 0;
}
