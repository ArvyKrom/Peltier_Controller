/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32g0xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define Temp_Down_Btn_Pin GPIO_PIN_1
#define Temp_Down_Btn_GPIO_Port GPIOA
#define Temp_Down_Btn_EXTI_IRQn EXTI0_1_IRQn
#define LT8722_CS_Pin GPIO_PIN_6
#define LT8722_CS_GPIO_Port GPIOA
#define LT8722_SWEN_Pin GPIO_PIN_10
#define LT8722_SWEN_GPIO_Port GPIOB
#define Temp_Up_Btn_Pin GPIO_PIN_12
#define Temp_Up_Btn_GPIO_Port GPIOB
#define Temp_Up_Btn_EXTI_IRQn EXTI4_15_IRQn
#define RED_LED_Pin GPIO_PIN_6
#define RED_LED_GPIO_Port GPIOC
#define OLED_D07_Pin GPIO_PIN_0
#define OLED_D07_GPIO_Port GPIOD
#define OLED_D06_Pin GPIO_PIN_1
#define OLED_D06_GPIO_Port GPIOD
#define OLED_D04_Pin GPIO_PIN_2
#define OLED_D04_GPIO_Port GPIOD
#define OLED_D05_Pin GPIO_PIN_3
#define OLED_D05_GPIO_Port GPIOD
#define OLED_RW_Pin GPIO_PIN_3
#define OLED_RW_GPIO_Port GPIOB
#define OLED_EN_Pin GPIO_PIN_4
#define OLED_EN_GPIO_Port GPIOB
#define OLED_RS_Pin GPIO_PIN_5
#define OLED_RS_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
