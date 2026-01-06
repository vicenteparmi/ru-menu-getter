#!/usr/bin/env python3
"""
Pydantic models for UTFPR menu data structure.
Ensures correct JSON format for Firebase database.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict
from datetime import datetime


class DayMenu(BaseModel):
    """Schema for a single day's menu."""
    menu: List[List[str]] = Field(
        description="Array of 3 meal periods: [café/lanche, almoço, jantar]. Each is a list of dishes."
    )
    timestamp: int = Field(
        default=0, 
        description="Unix timestamp, will be set on upload"
    )
    weekday: str = Field(
        description="Day of week in Portuguese, e.g. 'Segunda-Feira'"
    )
    
    @field_validator('menu')
    @classmethod
    def validate_menu_structure(cls, v):
        """Ensure menu has exactly 3 meal periods."""
        if len(v) != 3:
            # Pad with empty periods if needed
            while len(v) < 3:
                v.append(["Sem refeições disponíveis"])
        return v
    
    @field_validator('weekday')
    @classmethod
    def capitalize_weekday(cls, v):
        """Ensure weekday is properly capitalized."""
        return v.title() if v else "Desconhecido"


class WeeklyMenu(BaseModel):
    """Schema for a week's menu with dynamic date keys."""
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
                    "items": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "timestamp": {
                    "type": "integer",
                    "description": "Unix timestamp, always 0"
                },
                "weekday": {
                    "type": "string",
                    "description": "Day of week in Portuguese, e.g. 'Segunda-Feira'"
                }
            },
            "required": ["menu", "timestamp", "weekday"]
        }
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
    
    for date_str, day_data in data.items():
        try:
            # Validate date format
            datetime.strptime(date_str, "%Y-%m-%d")
            
            # Validate and create DayMenu
            day_menu = DayMenu(**day_data)
            processed[date_str] = day_menu.model_dump()
            
        except ValueError as e:
            errors.append(f"Date {date_str}: {str(e)}")
        except Exception as e:
            errors.append(f"Date {date_str}: {str(e)}")
    
    is_valid = len(errors) == 0
    return is_valid, processed, errors
