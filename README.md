# Process Scheduling Visualizer with Attention Mechanism

An interactive Python application with Tkinter GUI that visualizes CPU scheduling algorithms with an innovative attention-based decision layer. This educational tool helps understand process scheduling concepts in operating systems through real-time simulation and visualization.

Date: January 6, 2025

---

##  Project Overview

This visualizer simulates four classic CPU scheduling algorithms while implementing a novel **Attention Mechanism** that intelligently selects processes based on multiple weighted factors. The system provides side-by-side comparison between traditional algorithms and the attention-based approach.

###  Key Features

- **Four Scheduling Algorithms**:
  - First-Come-First-Serve (FCFS)
  - Shortest Job First (SJF)
  - Priority Scheduling
  - Round Robin (RR)

- **Innovative Attention Mechanism**:
  - Multi-factor weighted scoring system
  - Real-time decision visualization
  - Comparison between attention and traditional choices

- **Interactive Visualization**:
  - Live Gantt chart display
  - Ready/Waiting queue visualization
  - Attention score breakdown
  - Performance metrics calculation

- **User-Friendly Interface**:
  - Process input with validation
  - Step-by-step simulation control
  - Pause/Resume functionality
  - Color-coded visual elements

---
---

## Technology Stack

- **Programming Language**: Python 3.x
- **GUI Framework**: Tkinter
- **Visualization**: Custom Canvas-based rendering
- **Architecture**: Object-oriented design with MVC pattern

---

##  Project Structure
ProcessSchedulingVisualizer/
├── main.py # Main application entry point
├── process.py # Process class with attention mechanism
├── scheduler.py # Scheduling algorithm implementations
├── visualizer.py # GUI and visualization components
├── attention_engine.py # Attention scoring logic
└── utils.py # Utility functions and constants

---

##  Installation & Usage

### Prerequisites
```bash
# Python 3.8 or higher
python --version
```

# Tkinter (usually comes with Python)
# On Ubuntu/Debian:
```bash
sudo apt-get install python3-tk
```
# Clone or download the project files
```bash
git clone <repository-url>
cd ProcessSchedulingVisualizer
```

# Run the main application
```bash
python main.py
```
