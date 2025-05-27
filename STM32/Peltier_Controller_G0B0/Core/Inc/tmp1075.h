#ifndef __TMP1075
#define __TMP1075

#define TEMP_reg_addr 0x00
#define CONF_reg_addr 0x01
#define LOW_lim_reg_addr 0x02
#define HIGH_lim_reg_addr 0x03
#define DEV_id_addr 0x0F

#define TMP1075_1_addr 0x90 // Used outside of the chamber
#define TMP1075_2_addr 0x92 // Used at the inside of the chamber

int read_reg(I2C_HandleTypeDef *hi2c, uint16_t dev_addr, uint8_t reg_addr, uint8_t *rx_data, uint8_t size);
int read_temp(I2C_HandleTypeDef *hi2c, uint8_t dev_addr, double *temp);

#endif
