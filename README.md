# SportSpot: Sports Management Web Application

SportSpot is a Django-based web application designed to manage sporting events in the NYC metropolitan area. It enables users to browse events, sign up for participation, and engage in features like live drafts and tournament management.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Challenges and Solutions](#challenges-and-solutions)
- [Future Enhancements](#future-enhancements)
- [Setup Instructions](#setup-instructions)
- [License](#license)

---

## Overview

SportSpot creates an online catalog of sporting events, allowing users to explore and register for events. Designed with scalability in mind, the application predicts approximately 300 active users in the NYC area. 

---

## Features

- Models for games, users, and personal ratings.
- Event browsing and detailed views for users.
- Admin panel with the ability to:
  - Create and manage events and users.
  - Oversee tournaments and remove users.
- Live Draft functionality for real-time tournament setup.
- Moderator role for managing live drafts.

---

## Architecture

### Backend:
- **Framework**: Django
- **Database**: PostgreSQL
- **Authentication**: Django’s built-in authentication
- **Live Drafts**: WebSocket integration for real-time updates (future enhancement)

### Frontend:
- **Template Engine**: Django Templates
- **Basic Styling**: Bootstrap-based (to be improved)

### Deployment:
- **Cloud Hosting**: Render
- **Version Control**: Git and GitHub

---

## Challenges and Solutions

### 1. **User Management:**
   - **Challenge**: Managing user roles (admin, moderator, participant) dynamically.
   - **Solution**: Extended Django's user model and utilized custom permissions.

### 2. **Real-Time Drafts:**
   - **Challenge**: Implementing live draft sessions efficiently.
   - **Solution**: Used Django Channels for WebSocket-based real-time data updates.

### 3. **Scalability:**
   - **Challenge**: Designing the application to handle a growing user base.
   - **Solution**: Optimized database queries and reduced redundant operations in the backend.

---

## Future Enhancements

1. **UI/UX Improvement:**
   - Redesign the user interface for better aesthetics and usability.

2. **Paywall Integration:**
   - Add payment options for individual tournaments and season-long passes.

3. **Enhanced Features:**
   - User stats page, game score page, and tournament management dashboard.
   - Contact page or live chat functionality for real-time support.

4. **Advanced Analytics:**
   - Incorporate user behavior analytics to improve engagement.

---

## Setup Instructions

### Prerequisites:
- Python 3.8+
- PostgreSQL
- Git

### Steps:
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/haltaf000/SportSpot.git
   cd SportSpot
2. Install Dependencies:
   pip install -r requirements.txt
3. Set Up Database:
   Update DATABASES in settings.py with your PostgreSQL credentials.
   run migrations
   

