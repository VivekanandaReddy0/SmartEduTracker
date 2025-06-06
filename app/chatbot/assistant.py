import logging
import os
import json
from flask import current_app
from app.models import ChatHistory, db
from flask_login import current_user
from openai import OpenAI

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024
# do not change this unless explicitly requested by the user
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Fallback responses for system without API key
FALLBACK_RESPONSES = {
    "general": [
        "I'm here to help with your educational questions. What subject are you interested in?",
        "Feel free to ask me about any academic topic you're struggling with.",
        "I can provide guidance on study techniques, specific subjects, or educational resources.",
        "What educational topic would you like help with today?",
    ]
}

def get_ai_response(message, history=[]):
    """
    Generate a contextual educational response based on the user's message using OpenAI's API
    
    Args:
        message (str): User message
        history (list): List of previous messages in the conversation
    
    Returns:
        str: AI response
    """
    try:
        # Check if API key is available
        if not os.environ.get("OPENAI_API_KEY"):
            logging.warning("OpenAI API key not found. Using fallback responses.")
            return "I'm here to help with your educational questions. What topic would you like assistance with?"
        
        # Format conversation history for OpenAI
        system_message = """You are an educational assistant for the SmartEdu student portal, designed to support students in their academic journey.

Your primary goals are to:
1. Provide clear, accurate explanations of educational concepts
2. Offer practical study techniques and learning strategies
3. Help with problem-solving approaches (without solving specific homework problems)
4. Recommend educational resources appropriate for university students
5. Provide motivation and support for academic challenges

Important contexts:
- You are speaking to university students who are using the SmartEdu portal
- Students can view their attendance, grades, and academic progress in the portal
- Common subjects include Mathematics, Physics, Chemistry, Programming, Data Structures, and Engineering topics
- Focus on being supportive, encouraging critical thinking, and promoting good study habits

Keep responses concise (under 200 words), educational, and end with a follow-up question when appropriate to encourage engagement.
"""
        
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add conversation history if available
        if history:
            for entry in history:
                if 'user' in entry:
                    messages.append({"role": "user", "content": entry['user']})
                if 'assistant' in entry:
                    messages.append({"role": "assistant", "content": entry['assistant']})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",  # Using the latest model
            messages=messages,
            max_tokens=250,
            temperature=0.7,
        )
        
        # Extract response text
        ai_response = response.choices[0].message.content.strip()
        
        # Store chat history if user is logged in
        if current_user and not current_user.is_anonymous:
            try:
                chat_entry = ChatHistory(
                    user_id=current_user.id,
                    message=message,
                    response=ai_response
                )
                db.session.add(chat_entry)
                db.session.commit()
            except Exception as e:
                logging.error(f"Error saving chat history: {str(e)}")
                db.session.rollback()
        
        return ai_response
        
    except Exception as e:
        logging.error(f"Error in get_ai_response: {str(e)}")
        # Log the full error for debugging
        import traceback
        logging.error(traceback.format_exc())
        
        # Return a helpful message if there's an API issue
        return "I'm having trouble connecting to my knowledge base right now. Please try again in a moment, or ask about study techniques and educational strategies I can help with directly."
