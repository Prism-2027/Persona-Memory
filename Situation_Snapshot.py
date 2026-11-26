from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Timestamps(BaseModel):
    situation_detected_at: Optional[str] = None
    first_event_at: Optional[str] = None
    last_event_at: Optional[str] = None
    snapshot_generated_at: Optional[str] = None


class Trigger(BaseModel):
    primary_event_type: str
    primary_source: str
    trigger_event_id: str
    trigger_description: str


class PersonEntity(BaseModel):
    person_id: Optional[str] = None
    name: Optional[str] = None
    role_in_situation: Optional[str] = None
    contact_identifier: Optional[str] = None


class Entities(BaseModel):
    people: List[PersonEntity] = Field(default_factory=list)
    organizations: List[Any] = Field(default_factory=list)
    locations: List[Any] = Field(default_factory=list)
    devices: List[Any] = Field(default_factory=list)


class PhoneCall(BaseModel):
    available: Optional[bool] = None
    call_id: Optional[str] = None
    caller_id: Optional[str] = None
    phone_number: Optional[str] = None
    direction: Optional[str] = None
    call_status: Optional[str] = None
    call_start_time: Optional[str] = None
    call_end_time: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    missed_call: Optional[bool] = None
    call_frequency: Optional[int] = None
    previous_interaction_count: Optional[int] = None
    last_interaction: Optional[str] = None


class WhatsApp(BaseModel):
    available: Optional[bool] = None
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    direction: Optional[str] = None
    message_type: Optional[str] = None
    message_text: Optional[str] = None
    message_timestamp: Optional[str] = None
    is_group_message: Optional[bool] = None
    group_name: Optional[str] = None
    reply_received: Optional[bool] = None
    reply_time: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_description: Optional[str] = None
    unread_message_count: Optional[int] = None
    message_frequency: Optional[int] = None
    conversation_context: Optional[str] = None


class SMS(BaseModel):
    available: Optional[bool] = None
    message_id: Optional[str] = None
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    direction: Optional[str] = None
    message_text: Optional[str] = None
    message_timestamp: Optional[str] = None
    is_unread: Optional[bool] = None
    attachment_type: Optional[str] = None


class Email(BaseModel):
    available: Optional[bool] = None
    email_id: Optional[str] = None
    thread_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_email: Optional[str] = None
    recipient_ids: List[str] = Field(default_factory=list)
    cc_ids: List[str] = Field(default_factory=list)
    subject: Optional[str] = None
    body_summary: Optional[str] = None
    message_timestamp: Optional[str] = None
    is_read: Optional[bool] = None
    is_important: Optional[bool] = None
    priority: Optional[str] = None
    requires_response: Optional[bool] = None
    extracted_intent: Optional[str] = None
    extracted_deadline: Optional[str] = None
    attachment_types: List[str] = Field(default_factory=list)
    conversation_context: Optional[str] = None


class OtherMessagingApps(BaseModel):
    available: Optional[bool] = None
    platform: Optional[str] = None
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    sender_id: Optional[str] = None
    message_type: Optional[str] = None
    message_summary: Optional[str] = None
    message_timestamp: Optional[str] = None
    requires_response: Optional[bool] = None


class Communication(BaseModel):
    phone_call: PhoneCall = Field(default_factory=PhoneCall)
    whatsapp: WhatsApp = Field(default_factory=WhatsApp)
    sms: SMS = Field(default_factory=SMS)
    email: Email = Field(default_factory=Email)
    other_messaging_apps: OtherMessagingApps = Field(default_factory=OtherMessagingApps)


class NotificationEvent(BaseModel):
    available: Optional[bool] = None
    notification_id: Optional[str] = None
    app_name: Optional[str] = None
    sender_id: Optional[str] = None
    title: Optional[str] = None
    body_summary: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    timestamp: Optional[str] = None
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class DigitalActivity(BaseModel):
    screen_state: Optional[str] = None
    phone_locked: Optional[bool] = None
    foreground_app: Optional[str] = None
    app_category: Optional[str] = None
    current_device_usage: Optional[str] = None
    recent_app_activity: List[Any] = Field(default_factory=list)
    notification_count: Optional[int] = None
    notification_event: NotificationEvent = Field(default_factory=NotificationEvent)
    dnd_enabled: Optional[bool] = None
    silent_mode: Optional[bool] = None
    battery_level: Optional[int] = None
    charging_status: Optional[str] = None


class CalendarEvent(BaseModel):
    event_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    event_type: Optional[str] = None
    is_ongoing: Optional[bool] = None


class CalendarAndSchedule(BaseModel):
    available: Optional[bool] = None
    current_event: CalendarEvent = Field(default_factory=CalendarEvent)
    upcoming_events: List[CalendarEvent] = Field(default_factory=list)
    next_event_time: Optional[str] = None
    free_time_available: Optional[bool] = None
    schedule_conflict: Optional[bool] = None
    reminders: List[Any] = Field(default_factory=list)


class WearableAndHealthSignals(BaseModel):
    available: Optional[bool] = None
    heart_rate_bpm: Optional[int] = None
    resting_heart_rate_bpm: Optional[int] = None
    heart_rate_trend: Optional[str] = None
    heart_rate_variability_ms: Optional[float] = None
    blood_oxygen_percentage: Optional[float] = None
    skin_temperature_celsius: Optional[float] = None
    steps: Optional[int] = None
    steps_last_5_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    sleep_duration_hours: Optional[float] = None
    sleep_quality: Optional[str] = None
    stress_indicator: Optional[str] = None
    activity_recognition: Optional[str] = None
    workout_type: Optional[str] = None
    workout_duration_minutes: Optional[int] = None
    motion_level: Optional[str] = None
    posture: Optional[str] = None
    sensor_timestamp: Optional[str] = None
    sensor_quality: Optional[str] = None


class LocationAndMobility(BaseModel):
    available: Optional[bool] = None
    location: Optional[str] = None
    location_type: Optional[str] = None
    location_accuracy_meters: Optional[float] = None
    movement_state: Optional[str] = None
    speed_meters_per_second: Optional[float] = None
    travel_mode: Optional[str] = None
    destination: Optional[str] = None
    estimated_arrival_time: Optional[str] = None
    time_at_current_location_minutes: Optional[int] = None
    location_history_summary: Optional[str] = None


class EnvironmentAndIoT(BaseModel):
    available: Optional[bool] = None
    ambient_noise_level: Optional[float] = None
    noise_classification: Optional[str] = None
    ambient_light_level: Optional[float] = None
    room_temperature_celsius: Optional[float] = None
    motion_detected: Optional[bool] = None
    nearby_device_signals: List[Any] = Field(default_factory=list)
    connected_device_states: List[Any] = Field(default_factory=list)
    environment_summary: Optional[str] = None


class UserInteraction(BaseModel):
    available: Optional[bool] = None
    last_user_action: Optional[str] = None
    last_user_action_timestamp: Optional[str] = None
    recent_interactions: List[Any] = Field(default_factory=list)
    user_response_to_previous_notification: Optional[str] = None
    notification_dismissed: Optional[bool] = None
    interaction_frequency: Optional[str] = None


class TemporalContext(BaseModel):
    time_of_day: Optional[str] = None
    day_of_week: Optional[str] = None
    is_weekend: Optional[bool] = None
    is_holiday: Optional[bool] = None
    local_timezone: Optional[str] = None
    duration_of_current_situation_seconds: Optional[int] = None


class PersonaContext(BaseModel):
    memory_enriched: bool = False
    memory_references: List[str] = Field(default_factory=list)
    retrieved_facts: List[str] = Field(default_factory=list)
    context_source: Optional[str] = None


class Perception(BaseModel):
    situation_type: str
    situation_subtype: str
    detected_user_activity: Optional[str] = None
    detected_user_state: Optional[str] = None
    urgency: str = "unknown"
    importance: str = "unknown"
    confidence: float
    uncertainties: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    reason_for_snapshot: str


class Evidence(BaseModel):
    event_ids: List[str] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
    observation_count: int = 0
    data_quality: Optional[str] = None


class PrivacyAndPermissions(BaseModel):
    consent_verified: bool = True
    permitted_sources: List[str] = Field(default_factory=list)
    restricted_fields_present: bool = False


class OtherSignal(BaseModel):
    source: str
    event_type: str
    timestamp: Optional[str] = None
    observations: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None


class Situation(BaseModel):
    schema_version: str = "1.0"
    situation_id: str
    user_id: str
    timestamps: Timestamps = Field(default_factory=Timestamps)
    trigger: Trigger
    entities: Entities = Field(default_factory=Entities)
    communication: Communication = Field(default_factory=Communication)
    digital_activity: DigitalActivity = Field(default_factory=DigitalActivity)
    calendar_and_schedule: CalendarAndSchedule = Field(default_factory=CalendarAndSchedule)
    wearable_and_health_signals: WearableAndHealthSignals = Field(default_factory=WearableAndHealthSignals)
    location_and_mobility: LocationAndMobility = Field(default_factory=LocationAndMobility)
    environment_and_iot: EnvironmentAndIoT = Field(default_factory=EnvironmentAndIoT)
    user_interaction: UserInteraction = Field(default_factory=UserInteraction)
    temporal_context: TemporalContext = Field(default_factory=TemporalContext)
    persona_context: PersonaContext = Field(default_factory=PersonaContext)
    perception: Perception
    evidence: Evidence = Field(default_factory=Evidence)
    privacy_and_permissions: PrivacyAndPermissions = Field(default_factory=PrivacyAndPermissions)
    other_signals: List[OtherSignal] = Field(default_factory=list)
