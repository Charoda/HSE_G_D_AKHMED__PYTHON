
# activelifeuser.py

import asyncio
import asyncpg
from datetime import datetime
import os
from dotenv import load_dotenv


load_dotenv()


class User:
    """ Указывайте вес в кг, рост в метрах"""
    def __init__(self, name:str =None, weight:float = None, height: float  = None, age: int  = None, city: str  = None, water_norm: float = None, calories_norm: float = None):
        self.__name = name
        self.__weight = weight
        self.__height = height
        self.__age = age
        self.__city = city
        self.__activity = 0
        self.__water_norm = self.__calcWaterNorm(self.__weight, water_norm)
        self.__calories_norm = self.__calcCaloriesNorm(self.__weight, self.__height, self.__age, calories_norm)


    @property
    def name(self):
        return self.__name

    @property
    def weight(self):
        return self.__weight
    
    @property
    def height(self):
        return self.__height
    
    @property
    def age(self):
        return self.__age
    
    @property
    def city(self):
        return self.__city

    @name.setter
    def name(self, name : str):
        self.__name = name

    @property
    def water_norm(self):
        return self.__water_norm
    
    @property
    def activity(self):
        return self.__activity
    
    @activity.setter
    def activity(self, activity:int):
        self.__activity = activity
        
    @property
    def calories_norm(self):
        return self.__calories_norm

    # норма воды в литрах 
    @staticmethod
    def __calcWaterNorm(weight:int, water_norm):
        if ((water_norm is not None) & (water_norm != 0)):
            return water_norm
        if (weight is None):
            return 0
        return weight*30

    # норма калорий 
    @staticmethod
    def __calcCaloriesNorm(wight:int, height:int, age:int, calories_norm:float):
        if ((calories_norm is not None) & (calories_norm != 0)):
            return calories_norm
        if ((wight is None) or (height is None) or (age is None)):
            raise ValueError("не введены рост, вес и возраст")
        result = 10 * wight + 6.25 * height - 5 * age
        print(f'calc_calorie: {result}')
        return result

    def __str__(self):
        return f'---- Пользователь {self.__name}, норма воды: {self.__water_norm} л., норма калорий: {self.__calories_norm} к. ---\n'\
        f'---  рост: {self.__height} м., вес: {self.__weight} кг., возраст: {self.__age} лет ----'
    