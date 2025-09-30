# Backend of Agatha Christie Death on the Cards, Web version

## Idea
*Agatha Christie: Death on the Cards* is a multiplayer murder mystery card game inspired by the classic works of Agatha Christie. Players assume different roles, each with their own clues and secret objectives, and work together (or against each other) to solve a fictional murder.

This repository contains the backend for the web version of the card game.
## Configuration

### Cloning the Repository

To clone the repository, use the following command:
```
git clone https://github.com/Tripulacion-Barba-Azul/Backend.git
```

### Creating a Virtual Environment

On Windows:
```
python -m venv .venv
```
On Linux/MacOS:
```
python3 -m venv .venv
```

### Activating the Virtual Environment
On Windows:
```
.venv\Scripts\activate
```
On Linux/MacOS:
```
source env/bin/activate
```

### Installing Dependencies
```
cd Backend
pip install -r requirements.txt
```

## How to run

1. Navigate to the application directory:
```
cd src
```
2. Run the server:
```
fastapi dev main.py
```

## How to Stop the Server and Deactivate the Virtual Environment

### Stopping the Server
```
Ctrl + C
```

### Deactivating the Virtual Environment
```
deactivate
```