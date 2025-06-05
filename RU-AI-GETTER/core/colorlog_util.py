# colorlog_util.py
"""
Utilitário para colorir logs no terminal (CLI) usando ANSI.
"""

def color(text, fg=None, style=None):
    colors = {
        'black': 30, 'red': 31, 'green': 32, 'yellow': 33, 'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37,
        'gray': 90, 'bright_red': 91, 'bright_green': 92, 'bright_yellow': 93, 'bright_blue': 94, 'bright_magenta': 95, 'bright_cyan': 96, 'bright_white': 97
    }
    styles = {'bold': 1, 'underline': 4, 'reverse': 7}
    seq = []
    if style in styles:
        seq.append(str(styles[style]))
    if fg in colors:
        seq.append(str(colors[fg]))
    if seq:
        return f"\033[{';'.join(seq)}m{text}\033[0m"
    return text

def success(text):
    return color(text, fg='green', style='bold')

def warning(text):
    return color(text, fg='yellow', style='bold')

def error(text):
    return color(text, fg='red', style='bold')

def info(text):
    return color(text, fg='cyan')

def highlight(text):
    return color(text, fg='magenta', style='bold')
