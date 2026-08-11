#!/usr/bin/env python3
"""
Pydantic models for UTFPR menu data structure.
Ensures correct JSON format for Firebase database.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, List, Literal
from datetime import datetime


Weekday = Literal[
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
    "Domingo",
]

WEEKDAYS_PT: tuple[Weekday, ...] = (
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
    "Domingo",
)


class DayMenu(BaseModel):
    """Schema for a single day's menu."""
    model_config = ConfigDict(extra="forbid", strict=True)

    menu: List[List[str]] = Field(
        min_length=3,
        max_length=3,
        description="Array of 3 meal periods: [café/lanche, almoço, jantar]. Each is a list of dishes."
    )
    timestamp: Literal[0] = Field(
        default=0,
        description="Unix timestamp, will be set on upload"
    )
    weekday: Weekday = Field(
        description="Day of week in Portuguese, e.g. 'Segunda-Feira'"
    )
    
    @field_validator('menu')
    @classmethod
    def validate_menu_structure(cls, v):
        """Ensure every meal period contains non-empty dish names."""
        for period in v:
            if not period:
                raise ValueError("Each meal period must contain at least one item")
            if any(not item.strip() for item in period):
                raise ValueError("Meal items must be non-empty strings")
        return v


class WeeklyMenu(BaseModel):
    """Schema for a week's menu with dynamic date keys."""
    model_config = ConfigDict(extra="forbid", strict=True)

    days: Dict[str, DayMenu] = Field(
        description="Dictionary with date keys (YYYY-MM-DD) mapping to DayMenu objects"
    )
    
    @field_validator('days')
    @classmethod
    def validate_date_format(cls, v):
        """Ensure all keys are valid date strings."""
        for key in v.keys():
            try:
                datetime.strptime(key, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {key}. Expected YYYY-MM-DD")
        return v


def get_menu_json_schema() -> dict:
    """
    Returns a JSON schema for the menu structure that Gemini can use.
    This is a simplified schema for direct date-keyed output.
    """
    return {
        "type": "object",
        "description": "Menu data with date keys in YYYY-MM-DD format",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "menu": {
                    "type": "array",
                    "description": "Array of 3 meal periods: [café/lanche, almoço, jantar]",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                },
                "timestamp": {
                    "type": "integer",
                    "enum": [0],
                    "description": "Unix timestamp, always 0"
                },
                "weekday": {
                    "type": "string",
                    "enum": list(WEEKDAYS_PT),
                    "description": "Day of week in Portuguese, e.g. 'Segunda-Feira'"
                }
            },
            "required": ["menu", "timestamp", "weekday"],
            "additionalProperties": False
        },
        "minProperties": 1
    }


def validate_menu_data(data: dict) -> tuple[bool, dict, list]:
    """
    Validate menu data against the schema.
    
    Args:
        data: Raw menu dictionary from Gemini
        
    Returns:
        Tuple of (is_valid, processed_data, errors)
    """
    errors = []
    processed = {}

    if not isinstance(data, dict) or not data:
        return False, {}, ["Menu must be a non-empty object keyed by YYYY-MM-DD dates"]
    
    for date_str, day_data in data.items():
        try:
            # Validate date format
            menu_date = datetime.strptime(date_str, "%Y-%m-%d")

            if not isinstance(day_data, dict):
                raise ValueError("Day menu must be an object")
            
            # Validate and create DayMenu
            day_menu = DayMenu(**day_data)

            expected_weekday = WEEKDAYS_PT[menu_date.weekday()]
            if day_menu.weekday != expected_weekday:
                raise ValueError(
                    f"Weekday {day_menu.weekday!r} does not match {date_str}; expected {expected_weekday!r}"
                )

            processed[date_str] = day_menu.model_dump()
            
        except ValueError as e:
            errors.append(f"Date {date_str}: {str(e)}")
        except Exception as e:
            errors.append(f"Date {date_str}: {str(e)}")
    
    is_valid = len(errors) == 0
    return is_valid, processed, errors
