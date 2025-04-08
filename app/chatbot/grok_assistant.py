import logging
import os
import json
from flask import current_app
from app.models import ChatHistory, db
from flask_login import current_user
from openai import OpenAI

# Initialize xAI client with OpenAI client interface (Grok uses a compatible API)
xai_client = OpenAI(
    base_url="https://api.x.ai/v1", 
    api_key=os.environ.get("XAI_API_KEY")
)

def get_grok_response(message, history=[]):
    """
    Generate a contextual educational response based on the user's message using xAI's Grok model
    
    Args:
        message (str): User message
        history (list): List of previous messages in the conversation
    
    Returns:
        str: AI response
    """
    try:
        # Check if API key is available
        if not os.environ.get("XAI_API_KEY"):
            logging.warning("xAI API key not found. Please use OpenAI instead.")
            return "I'm unable to connect to the Grok model right now. Please try OpenAI instead or contact your administrator."
        
        # Format conversation history for xAI
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
        
        # Call xAI Grok API
        response = xai_client.chat.completions.create(
            model="grok-2-1212",  # Using the Grok-2 model
            messages=messages,
            max_tokens=300,
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
        logging.error(f"Error in get_grok_response: {str(e)}")
        # Log the full error for debugging
        import traceback
        logging.error(traceback.format_exc())
        
        # Return a helpful message if there's an API issue
        return "I'm having trouble connecting to my knowledge base right now. Please try again in a moment, or ask about study techniques and educational strategies I can help with directly."