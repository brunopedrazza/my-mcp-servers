import os
import pickle
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import Dict, List, Optional, Literal, TypedDict
from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from mcp.server.fastmcp import FastMCP
from tzlocal import get_localzone

# Define return type for better type hinting
class CalendarEventResult(TypedDict):
    success: bool
    message: str
    event_link: Optional[str]
    conference_link: Optional[str]

# Add new type for list events response
class CalendarEvent(TypedDict):
    title: str
    start_time: str
    end_time: str
    description: str
    event_link: str
    conference_link: Optional[str]

class ListEventsResult(TypedDict):
    success: bool
    message: str
    events: List[CalendarEvent]

mcp = FastMCP("calendar")

def get_credentials():
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), '..', 'token.pickle')
    credentials_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise Exception("credentials.json file not found. Please set up Google Calendar API credentials first. Tried to get credentials from: " + credentials_path)
            
            scopes = ['https://www.googleapis.com/auth/calendar']
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds

def format_datetime_for_google(dt_str, timezone_str):
    """Convert datetime string to RFC3339 format with Z timezone indicator"""
    try:
        # If datetime is already provided in ISO format
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        # If datetime is None or invalid, return None
        return None

    # Convert to UTC
    tz = pytz.timezone(timezone_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    utc_dt = dt.astimezone(pytz.UTC)
    
    # Format in RFC3339 format
    return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def validate_gmt_timezone(timezone_str: str) -> str:
    """Validates that timezone is in GMT±X format and returns the Etc/GMT∓X format.
    
    Args:
        timezone_str: Timezone string in format 'GMT+X' or 'GMT-X'
        
    Returns:
        Timezone string in format 'Etc/GMT∓X' (note the reversed sign)
        
    Raises:
        ValueError: If timezone string is not in valid GMT±X format
    """
    if not timezone_str or not isinstance(timezone_str, str):
        raise ValueError("Timezone must be provided in GMT±X format (e.g. 'GMT+5', 'GMT-3')")
        
    timezone_str = timezone_str.upper().strip()
    if not timezone_str.startswith('GMT'):
        raise ValueError("Timezone must start with 'GMT'")
        
    try:
        # Extract the sign and number
        if len(timezone_str) < 5:  # Must be at least 'GMT+1'
            raise ValueError("Invalid GMT timezone format")
            
        sign = timezone_str[3]
        if sign not in ['+', '-']:
            raise ValueError("Timezone must include + or - after GMT")
            
        # Handle potential decimal points or extra characters
        offset_str = timezone_str[4:].strip()
        offset = int(float(offset_str))  # Convert to float first to handle decimal points
        
        if offset < 0 or offset > 12:
            raise ValueError("Timezone offset must be between 0 and 12")
            
        # For IANA/Olson timezone database, we need to reverse the sign and use Etc/GMT format
        # GMT+5 becomes Etc/GMT-5, GMT-3 becomes Etc/GMT+3
        reversed_sign = '-' if sign == '+' else '+'
        return f"Etc/GMT{reversed_sign}{offset}"
        
    except (IndexError, ValueError) as e:
        if str(e).startswith("Invalid GMT timezone format"):
            raise ValueError(str(e))
        raise ValueError(f"Invalid GMT timezone format. Must be in format GMT±X where X is between 0 and 12")

def create_calendar_event(summary, start_time, end_time, description="", timezone=None, attendees=None, add_conference=False, recurrence=None, send_updates='none'):
    try:
        # Get system timezone if none provided
        if timezone is None:
            local_tz = get_localzone()
            offset = datetime.now(local_tz).utcoffset().total_seconds() / 3600
            sign = '+' if offset > 0 else '-'
            abs_offset = abs(int(offset))
            # Ensure the timezone is in the correct GMT±X format
            timezone = f"GMT{sign}{abs_offset}"
            
            # Validate the generated timezone format
            try:
                validate_gmt_timezone(timezone)
            except ValueError:
                raise ValueError(f"Failed to generate valid GMT timezone from system timezone. System returned: {local_tz}")

        # Validate and convert timezone to IANA format
        iana_timezone = validate_gmt_timezone(timezone)
            
        # Format times in RFC3339
        start_time = format_datetime_for_google(start_time, iana_timezone)
        end_time = format_datetime_for_google(end_time, iana_timezone)
        
        if not start_time or not end_time:
            raise ValueError("Invalid start or end time format")
        
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': iana_timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': iana_timezone,
            },
        }

        # Add attendees if provided
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        # Add conference data if requested
        if add_conference:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': f"{summary}-{start_time}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }

        # Add recurrence if provided
        if recurrence:
            event['recurrence'] = recurrence

        # Create event with additional parameters
        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1 if add_conference else 0,
            sendUpdates=send_updates
        ).execute()

        return {
            "success": True,
            "message": f"Event created successfully in {timezone}. Event ID: {event.get('id')}",
            "event_link": event.get('htmlLink'),
            "conference_link": event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri') if add_conference else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create event: {str(e)}"
        }
    

def parse_relative_date(relative_date: str, timezone_str: str, start_hour: Optional[int] = None, base_time: Optional[datetime] = None) -> datetime:
    """Parse a relative date string into a datetime object.
    
    Important:
        - start_hour must be explicitly provided by the user
        - Never assume a default meeting time
        - If start_hour is not provided, raise an error asking for the time
    
    Args:
        relative_date: Date string to parse
        timezone_str: Timezone string in GMT±X format
        start_hour: Hour of the day (24-hour format) - Must be explicitly provided
        base_time: Optional reference time for relative dates
        
    Raises:
        ValueError: If start_hour is not provided or if date cannot be parsed
    """
    if start_hour is None:
        raise ValueError("Meeting time (start_hour) must be explicitly provided by the user in 24-hour format")

    # Convert GMT timezone to IANA format
    try:
        iana_timezone = validate_gmt_timezone(timezone_str)
        tz = pytz.timezone(iana_timezone)
    except Exception as e:
        raise ValueError(f"Invalid timezone format: {str(e)}")
        
    if base_time is None:
        base_time = datetime.now(tz)
    elif base_time.tzinfo is None:
        base_time = tz.localize(base_time)
    
    # Convert common phrases to dateutil-compatible format
    relative_date = relative_date.lower().strip()
    # Remove optional "for" prefix
    relative_date = relative_date.replace('for ', '')
    
    weekday_map = {
        'monday': MO, 'tuesday': TU, 'wednesday': WE,
        'thursday': TH, 'friday': FR, 'saturday': SA, 'sunday': SU
    }
    
    try:
        if relative_date == 'tomorrow':
            result = base_time + timedelta(days=1)
        elif relative_date == 'next week':
            result = base_time + timedelta(weeks=1)
        elif relative_date == 'next month':
            result = base_time + relativedelta(months=1)
        elif relative_date.startswith('next '):
            date_part = relative_date.split(' ', 1)[1]
            # Check if it's a weekday
            if date_part in weekday_map:
                result = base_time + relativedelta(weekday=weekday_map[date_part](+1))
            # Try to parse as a specific date
            else:
                try:
                    # Parse the date part without year
                    parsed_date = parse(date_part)
                    current_year = base_time.year
                    
                    # Create a datetime for this year's occurrence
                    target_date = tz.localize(datetime(
                        year=current_year,
                        month=parsed_date.month,
                        day=parsed_date.day
                    ))
                    
                    # If the date this year is in the past or less than 7 days in the future,
                    # use next year's date
                    if target_date < base_time or (target_date - base_time).days < 7:
                        target_date = tz.localize(datetime(
                            year=current_year + 1,
                            month=parsed_date.month,
                            day=parsed_date.day
                        ))
                    result = target_date
                except ValueError:
                    raise ValueError(f"Could not parse date: {date_part}")
        else:
            # If not a special case, try to parse as a regular date
            parsed = parse(relative_date, fuzzy=True)
            if parsed.tzinfo is None:
                parsed = tz.localize(parsed)
            result = parsed
            
        # Set the specified hour while preserving timezone
        return result.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    except ValueError as e:
        raise ValueError(f"Could not parse relative date: {relative_date}. Error: {str(e)}")

@mcp.tool()
async def create_event(
    title: str,  # Can be inferred from context
    description: str,  # Can be inferred from context
    relative_date: str,  # Required
    start_hour: int,  # Required, must be explicitly asked
    duration_minutes: int = 60,  # Use default unless user specifies otherwise
    timezone: str = None,  # Now expects GMT±X format (e.g. 'GMT+5', 'GMT-3')
    attendees: List[str] = [],  # Optional but recommend asking
    add_conference: bool = False,
    recurrence: List[str] = None,  # Ask if user mentions recurring
    send_updates: Literal["none", "all", "externalOnly"] = "none",
) -> CalendarEventResult:
    """Creates an event in the calendar of the user.

    ⚠️ TIMEZONE RULES - READ FIRST ⚠️:
    1. If user mentions ANY timezone-related terms (e.g. "pacific", "PST", "EST", "UTC", etc.):
       - You MUST specify the timezone parameter as GMT±X
       - Example: "pacific time" → timezone="GMT-7"
       - Example: "eastern time" → timezone="GMT-4"
       - NEVER skip this parameter if timezone is mentioned
       - NEVER rely on system timezone if user mentions a timezone
    2. Only use system timezone (timezone=None) if user makes NO mention of timezones

    Important:
        Before creating an event, the following information MUST be explicitly confirmed with the user:
        1. start_hour: Never assume a default time - ALWAYS ask the user for the specific hour
        
        Additionally, it's recommended to confirm:
        - attendees: Ask if they want to invite anyone
        - recurrence: If any mention of repetition, ask for specific pattern

        Note on title and description:
        - These can be intelligently inferred from the user's request
        - Use clear, descriptive titles based on the context
        - Add relevant details to the description based on the meeting type
        - No need to explicitly confirm these with the user unless the context is ambiguous

        Note on duration:
        - Default duration is 60 minutes
        - Use default unless user specifically mentions a different duration
        - No need to confirm the duration unless user's request implies a different length

    Args:
        title: Title of the event (can be inferred from context)
        description: Description of the event (can be inferred from context)
        relative_date: Date string (e.g., "next Monday", "next 04/01" for April 1st - use American format MM/DD, "next month", "tomorrow")
        start_hour: Hour of the day to schedule the event, in 24-hour format (e.g., 14 for 2:00 PM). 
                   Must be explicitly provided by user - do not assume a default time.
        duration_minutes: Duration in minutes (defaults to 60, no need to confirm unless user implies different duration)
        timezone: Timezone in GMT±X format (e.g., 'GMT+5', 'GMT-3')
                 MUST be specified if user mentions anything timezone-related
                 Only use system timezone if user makes no mention of timezone
        attendees: List of email addresses of the attendees (recommend asking user if they want to add any)
        add_conference: Whether to add a Google Meet conference to the event
        recurrence: RRULE strings for recurring events (e.g., ['RRULE:FREQ=DAILY;COUNT=2'])
                   If user mentions recurring/repeating/daily/weekly, ask for specifics
        send_updates: Whether to send updates to the attendees
            possible values: "none", "all", "externalOnly"

    Example Interactions:
        User: "Schedule a meeting for next Monday"
        Assistant should:
        - MUST ask: "What time would you like to schedule the meeting for? (24-hour format)"
        - Can infer: Set title as "Team Meeting" and appropriate description
        - Can use: Default 60-minute duration
        - Should ask: "Would you like to invite any attendees?"

        User: "Schedule a daily standup at 9am EST"
        Assistant should:
        - MUST specify: timezone as 'GMT-5' (for EST)
        - Can infer: Set title as "Daily Standup" and description about team sync
        - Can use: Default 15-30 minute duration (since it's a standup)
        - Should ask: "How many days should it repeat for?"
        - Should ask: "Would you like to invite any team members?"

        User: "Schedule team sync"
        Assistant should:
        - MUST ask: "When would you like to schedule the team sync?"
        - MUST ask: "What time would you like it to start? (24-hour format)"
        - Can infer: Set appropriate title and description for a team sync
        - Can use: Default 60-minute duration
        - Should ask: "Would you like this to be a recurring meeting?"
        - Should ask: "Would you like to add any attendees?"

    Returns:
        CalendarEventResult containing:
        - success: Whether the event was created successfully
        - message: Message from the API
        - event_link: Link to the event
        - conference_link: Link to the conference if add_conference was True
    """
    try:
        # Use system timezone if none provided
        if not timezone:
            local_tz = get_localzone()
            offset = datetime.now(local_tz).utcoffset().total_seconds() / 3600
            sign = '+' if offset > 0 else '-'
            abs_offset = abs(int(offset))
            event_timezone = f"GMT{sign}{abs_offset}"
        else:
            event_timezone = timezone
        
        # Parse the relative date and set the time to the specified hour
        start_datetime = parse_relative_date(relative_date, event_timezone, start_hour)
            
        # Calculate end time based on duration
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Convert to ISO format strings
        start_date = start_datetime.isoformat()
        end_date = end_datetime.isoformat()

    except ValueError as e:
        return CalendarEventResult(
            success=False,
            message=f"Failed to parse date or timezone: {str(e)}",
            event_link=None,
            conference_link=None
        )
    
    result = create_calendar_event(title, start_date, end_date, description, event_timezone, 
                               attendees, add_conference, recurrence, send_updates)
    
    return CalendarEventResult(
        success=result["success"],
        message=result["message"],
        event_link=result.get("event_link"),
        conference_link=result.get("conference_link")
    )

def list_calendar_events(start_time: str, end_time: str, timezone: str) -> List[Dict]:
    """List calendar events between start and end time.
    
    Args:
        start_time: Start time in RFC3339 format
        end_time: End time in RFC3339 format
        timezone: Timezone in IANA format
        
    Returns:
        List of calendar events with their details, with clickable markdown links
    """
    try:
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Get the raw links
            event_link = event.get('htmlLink', '')
            conference_link = event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri')
            
            # Format the links as clickable markdown if they exist
            formatted_event_link = f"[Click to view event]({event_link})" if event_link else ''
            formatted_conference_link = f"[Click to join meeting]({conference_link})" if conference_link else None
            
            formatted_event = {
                'title': event.get('summary', 'No title'),
                'start_time': start,
                'end_time': end,
                'description': event.get('description', ''),
                'event_link': formatted_event_link,
                'conference_link': formatted_conference_link
            }
            formatted_events.append(formatted_event)
            
        return formatted_events
        
    except Exception as e:
        raise Exception(f"Failed to list events: {str(e)}")

@mcp.tool()
async def list_events(
    relative_date: str,  # Required - e.g., "tomorrow", "next Monday"
    timezone: str = None,  # Optional - will use system timezone if not provided
) -> ListEventsResult:
    """List calendar events for a specific date range.
    
    This tool lists all calendar events for the specified date. It uses the same relative
    date parsing as the create_event function, making it easy to query for dates like
    "tomorrow", "next Monday", etc.
    
    Args:
        relative_date: Date string (e.g., "tomorrow", "next Monday", "next week")
        timezone: Timezone in GMT±X format (e.g., 'GMT+5', 'GMT-3').
                 If not provided, system timezone will be used.
                 
    Returns:
        ListEventsResult containing:
        - success: Whether the events were retrieved successfully
        - message: Status message
        - events: List of calendar events with their details including:
            - title: Event title
            - start_time: Start time
            - end_time: End time
            - description: Event description
            - event_link: Link to view the event
            - conference_link: Link to join conference (if applicable)
    """
    try:
        # Use system timezone if none provided
        if not timezone:
            local_tz = get_localzone()
            offset = datetime.now(local_tz).utcoffset().total_seconds() / 3600
            sign = '+' if offset > 0 else '-'
            abs_offset = abs(int(offset))
            event_timezone = f"GMT{sign}{abs_offset}"
        else:
            event_timezone = timezone
            
        # Convert GMT timezone to IANA format
        iana_timezone = validate_gmt_timezone(event_timezone)
        
        # Parse the start date - use midnight as start time
        start_datetime = parse_relative_date(relative_date, event_timezone, start_hour=0)
        # End datetime is end of the same day
        end_datetime = start_datetime.replace(hour=23, minute=59, second=59)
        
        # Convert to RFC3339 format
        start_time = format_datetime_for_google(start_datetime.isoformat(), iana_timezone)
        end_time = format_datetime_for_google(end_datetime.isoformat(), iana_timezone)
        
        # Get the events
        events = list_calendar_events(start_time, end_time, iana_timezone)
        
        return ListEventsResult(
            success=True,
            message=f"Successfully retrieved events for {relative_date}",
            events=events
        )
        
    except Exception as e:
        return ListEventsResult(
            success=False,
            message=f"Failed to list events: {str(e)}",
            events=[]
        )

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')