from django import forms
from .models import Vehicle, Driver, DeliveryRoute, DeliveryStop, DeliveryEvent
from logistics.models.notification_config import NotificationConfig

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = '__all__'

class DeliveryRouteForm(forms.ModelForm):
    class Meta:
        model = DeliveryRoute
        fields = '__all__'

class DeliveryStopForm(forms.ModelForm):
    class Meta:
        model = DeliveryStop
        fields = '__all__'

class DeliveryEventForm(forms.ModelForm):
    class Meta:
        model = DeliveryEvent
        fields = '__all__'

class NotificationConfigForm(forms.ModelForm):
    """
    Formulario para configurar notificaciones de logística
    """
    
    # Campos de eventos como checkboxes
    event_delayed = forms.BooleanField(
        required=False, 
        label='Entregas Retrasadas',
        help_text='Recibir notificaciones cuando una entrega se retrase'
    )
    event_out_geofence = forms.BooleanField(
        required=False, 
        label='Fuera de Geocerca',
        help_text='Recibir notificaciones cuando un vehículo salga de la geocerca'
    )
    event_incident = forms.BooleanField(
        required=False, 
        label='Incidentes',
        help_text='Recibir notificaciones de incidentes durante entregas'
    )
    event_weather_alert = forms.BooleanField(
        required=False, 
        label='Alertas Meteorológicas',
        help_text='Recibir notificaciones de alertas meteorológicas'
    )
    event_completed = forms.BooleanField(
        required=False, 
        label='Entregas Completadas',
        help_text='Recibir notificaciones cuando se complete una entrega'
    )
    
    # Campos de canales como checkboxes
    channel_email = forms.BooleanField(
        required=False, 
        label='Email',
        help_text='Recibir notificaciones por correo electrónico'
    )
    channel_push = forms.BooleanField(
        required=False, 
        label='Notificaciones Push',
        help_text='Recibir notificaciones push en dispositivos móviles'
    )
    channel_sms = forms.BooleanField(
        required=False, 
        label='SMS',
        help_text='Recibir notificaciones por mensaje de texto'
    )
    
    class Meta:
        model = NotificationConfig
        fields = ['role', 'receive_push', 'receive_email']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'receive_push': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar valores iniciales para eventos
        if self.instance.pk:
            events = self.instance.events or []
            self.fields['event_delayed'].initial = 'delayed' in events
            self.fields['event_out_geofence'].initial = 'out_geofence' in events
            self.fields['event_incident'].initial = 'incident' in events
            self.fields['event_weather_alert'].initial = 'weather_alert' in events
            self.fields['event_completed'].initial = 'completed' in events
            
            # Configurar valores iniciales para canales
            channels = self.instance.channels or []
            self.fields['channel_email'].initial = 'email' in channels
            self.fields['channel_push'].initial = 'push' in channels
            self.fields['channel_sms'].initial = 'sms' in channels
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Recopilar eventos seleccionados
        events = []
        if self.cleaned_data.get('event_delayed'):
            events.append('delayed')
        if self.cleaned_data.get('event_out_geofence'):
            events.append('out_geofence')
        if self.cleaned_data.get('event_incident'):
            events.append('incident')
        if self.cleaned_data.get('event_weather_alert'):
            events.append('weather_alert')
        if self.cleaned_data.get('event_completed'):
            events.append('completed')
        
        instance.events = events
        
        # Recopilar canales seleccionados
        channels = []
        if self.cleaned_data.get('channel_email'):
            channels.append('email')
        if self.cleaned_data.get('channel_push'):
            channels.append('push')
        if self.cleaned_data.get('channel_sms'):
            channels.append('sms')
        
        instance.channels = channels
        
        if commit:
            instance.save()
        return instance 