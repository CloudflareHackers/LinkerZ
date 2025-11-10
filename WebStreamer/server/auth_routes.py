# Authentication API routes
import logging
import json
from aiohttp import web
from WebStreamer.database import get_database

routes = web.RouteTableDef()

@routes.post("/api/auth/request-otp")
async def request_otp(request: web.Request):
    """Request OTP for Telegram user ID"""
    try:
        data = await request.json()
        telegram_user_id = data.get('telegram_user_id')
        
        if not telegram_user_id:
            return web.json_response({
                'success': False,
                'message': 'telegram_user_id is required'
            }, status=400)
        
        try:
            telegram_user_id = int(telegram_user_id)
        except ValueError:
            return web.json_response({
                'success': False,
                'message': 'Invalid telegram_user_id'
            }, status=400)
        
        # Generate OTP
        db = get_database()
        if not db.auth:
            return web.json_response({
                'success': False,
                'message': 'Authentication system not available'
            }, status=500)
        
        otp = db.auth.generate_otp(telegram_user_id)
        
        # In production, send OTP via bot
        # For now, we'll return it in response (this should be changed for production)
        # The bot will send the OTP to the user
        from WebStreamer.bot import StreamBot
        try:
            await StreamBot.send_message(
                chat_id=telegram_user_id,
                text=f"🔐 **Your OTP Code**\n\n"
                     f"Code: `{otp}`\n\n"
                     f"This code is valid for 10 minutes.\n"
                     f"To verify, send:\n`/verify {otp}`\n\n"
                     f"⚠️ Never share this code with anyone!"
            )
            
            return web.json_response({
                'success': True,
                'message': 'OTP sent to your Telegram account. Please check your messages.',
                'telegram_user_id': telegram_user_id
            })
        except Exception as e:
            logging.error(f"Failed to send OTP via bot: {e}")
            # Fallback: return OTP in response (for development/testing)
            return web.json_response({
                'success': True,
                'message': 'OTP generated (check bot for message)',
                'otp': otp,  # Remove this in production
                'telegram_user_id': telegram_user_id
            })
        
    except json.JSONDecodeError:
        return web.json_response({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logging.error(f"Error requesting OTP: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'message': 'Internal server error'
        }, status=500)

@routes.post("/api/auth/verify-otp")
async def verify_otp(request: web.Request):
    """Verify OTP and create session"""
    try:
        data = await request.json()
        telegram_user_id = data.get('telegram_user_id')
        otp = data.get('otp')
        
        if not telegram_user_id or not otp:
            return web.json_response({
                'success': False,
                'message': 'telegram_user_id and otp are required'
            }, status=400)
        
        try:
            telegram_user_id = int(telegram_user_id)
        except ValueError:
            return web.json_response({
                'success': False,
                'message': 'Invalid telegram_user_id'
            }, status=400)
        
        # Verify OTP
        db = get_database()
        if not db.auth:
            return web.json_response({
                'success': False,
                'message': 'Authentication system not available'
            }, status=500)
        
        verified = db.auth.verify_otp(telegram_user_id, otp)
        
        if not verified:
            return web.json_response({
                'success': False,
                'message': 'Invalid or expired OTP'
            }, status=401)
        
        # Get user info from request (if provided) or create basic user
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        username = data.get('username')
        
        # Create or update user record (required for foreign key constraint)
        db.auth.create_user(telegram_user_id, first_name, last_name, username)
        
        # Create session
        session_token = db.auth.create_session(telegram_user_id)
        
        if not session_token:
            return web.json_response({
                'success': False,
                'message': 'Failed to create session'
            }, status=500)
        
        # Get user info
        user = db.auth.get_user(telegram_user_id)
        
        response = web.json_response({
            'success': True,
            'message': 'Authentication successful',
            'session_token': session_token,
            'user': user
        })
        
        # Set session cookie
        response.set_cookie(
            'session_token',
            session_token,
            max_age=7*24*60*60,  # 7 days
            httponly=True,
            secure=True,
            samesite='Lax'
        )
        
        return response
        
    except json.JSONDecodeError:
        return web.json_response({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logging.error(f"Error verifying OTP: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'message': 'Internal server error'
        }, status=500)

@routes.get("/api/auth/session")
async def check_session(request: web.Request):
    """Check if session is valid"""
    try:
        # Get session token from cookie or Authorization header
        session_token = request.cookies.get('session_token')
        
        if not session_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                session_token = auth_header[7:]
        
        if not session_token:
            return web.json_response({
                'success': False,
                'authenticated': False,
                'message': 'No session token provided'
            }, status=401)
        
        # Validate session
        db = get_database()
        if not db.auth:
            return web.json_response({
                'success': False,
                'message': 'Authentication system not available'
            }, status=500)
        
        telegram_user_id = db.auth.validate_session(session_token)
        
        if not telegram_user_id:
            return web.json_response({
                'success': False,
                'authenticated': False,
                'message': 'Invalid or expired session'
            }, status=401)
        
        # Get user info
        user = db.auth.get_user(telegram_user_id)
        
        # Get rate limit info
        rate_limits = None
        if db.rate_limiter:
            rate_limits = db.rate_limiter.get_limits(telegram_user_id)
        
        return web.json_response({
            'success': True,
            'authenticated': True,
            'user': user,
            'rate_limits': rate_limits
        })
        
    except Exception as e:
        logging.error(f"Error checking session: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'message': 'Internal server error'
        }, status=500)

@routes.post("/api/auth/logout")
async def logout(request: web.Request):
    """Logout and invalidate session"""
    try:
        # Get session token
        session_token = request.cookies.get('session_token')
        
        if not session_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                session_token = auth_header[7:]
        
        if session_token:
            # Delete session from database
            db = get_database()
            if db.auth and db.conn:
                cursor = db.conn.cursor()
                cursor.execute("""
                    DELETE FROM login_sessions WHERE session_token = %s
                """, (session_token,))
                cursor.close()
        
        response = web.json_response({
            'success': True,
            'message': 'Logged out successfully'
        })
        
        # Clear cookie
        response.del_cookie('session_token')
        
        return response
        
    except Exception as e:
        logging.error(f"Error during logout: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'message': 'Internal server error'
        }, status=500)
