#ifndef __LT8722_H
#define __LT8722_H

// Make sure that SWEN, EN, and CS pins are defined so that they'd be available at main.h

#define Status_Acquisition_Command 0xF0
#define Data_Write_Command 0xF2
#define Data_Read_Command 0xF4

#define SLAVE_ACK 165

#define SPIS_Command_Reg_Addr 0
#define SPIS_Status_Reg_Addr 2
#define SPIS_DAC_ILIMN_Reg_Addr 4
#define SPIS_DAC_Reg_Addr 8
#define SPIS_AMUX_Reg_Addr 14
#define SPIS_AMUX_Reg_To_Read_Vout_Val 0x43
#define SPIS_AMUX_Reg_To_Read_V1P25_Val 0x46
#define SPIS_AMUX_Reg_To_Read_Iout_Val 0x44
#define SPIS_AMUX_Reg_To_Read_V1P65_Val 0x47
#define SPIS_Command_Reg_Default_Val 0x0AA214

#define MIN_POS_SPIS_DAC_Code 0xFF7A0000 // Shouldn't use lower than this
#define MAX_POS_Vout 10.14
#define MAX_NEG_SPIS_DAC_Code 0x008B0000 // Shouldn't use higher than this
#define MAX_NEG_Vout -10.50

int LT8722_Init(SPI_HandleTypeDef *hspi);
int read_lt8722_reg(SPI_HandleTypeDef *hspi, uint8_t *reg_addr, uint8_t *data, uint8_t size);
int write_lt8722_reg(SPI_HandleTypeDef *hspi, uint8_t *reg_addr, uint8_t *data, uint8_t size);
int status_aq(SPI_HandleTypeDef *hspi);
int set_vout(SPI_HandleTypeDef *hspi, double vout);
int is_load_connected(SPI_HandleTypeDef *hspi, ADC_HandleTypeDef *hadc);
uint8_t get_CRC8(const uint8_t *data, uint16_t length);

#endif
