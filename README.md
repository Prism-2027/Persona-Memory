# Persona Memory System

### Samsung PRISM — Perception, Memory, Prediction and Action Challenge

## Overview

The Persona Memory System is a dynamic memory architecture designed to maintain a structured representation of a user's identity, experiences, relationships, preferences, and behavioural patterns.

It consists of three interconnected memory components:

- **Episodic Memory:** Stores significant user experiences, events, and interactions.
- **Relationship Memory:** Maintains information about relationships, including closeness, trust, importance, and interaction patterns.
- **Value Memory:** Captures user preferences, priorities, personal values, and decision-making tendencies.

## Architecture

The system uses:

- **MongoDB:** Structured storage of persona memory records.
- **ChromaDB:** Vector storage and semantic retrieval of relevant memories.
- **Python:** Memory processing, management, and integration.
- **LLMs:** Information extraction, memory interpretation, and contextual reasoning.

## Workflow

1. Receives structured user information from the Perception Module.
2. Classifies information into Episodic, Relationship, and Value Memory.
3. Stores and continuously updates relevant memory records.
4. Retrieves relevant memories based on incoming Situation Snapshots.
5. Provides contextual information to the Prediction Module for personalized decision-making.

## Project Objective

To develop an evolving and context-aware representation of the user that enables personalized AI predictions and recommendations based on historical experiences, relationships, preferences, and behavioural patterns.

## Project Context

Developed as part of the Samsung PRISM — Perception, Memory, Prediction and Action Challenge.
