from logistics.models import DeliveryRoute, DeliveryStop, Vehicle, Driver
from django.db import transaction
from django.utils import timezone
from geopy.distance import geodesic

class RoutePlanningService:
    """
    Servicio para asignar paradas a rutas y optimizar el recorrido de los vehículos.
    Implementa un algoritmo básico de nearest neighbor (puede ser reemplazado por uno más avanzado).
    """
    def __init__(self, date=None):
        self.date = date or timezone.now().date()

    def plan_routes(self, stops_queryset=None, vehicles_queryset=None):
        """
        Asigna paradas a rutas y optimiza el orden de visita para cada vehículo disponible.
        """
        stops = list(stops_queryset or DeliveryStop.objects.filter(route__isnull=True, state='pending'))
        vehicles = list(vehicles_queryset or Vehicle.objects.filter(is_active=True))
        if not stops or not vehicles:
            return []
        planned_routes = []
        with transaction.atomic():
            for vehicle in vehicles:
                # Seleccionar paradas cercanas (puede mejorarse con clustering)
                assigned_stops = self._assign_stops_to_vehicle(vehicle, stops)
                if not assigned_stops:
                    continue
                route = DeliveryRoute.objects.create(
                    vehicle=vehicle,
                    driver=vehicle.driver_set.first(),
                    date=self.date,
                    state='planned',
                )
                ordered_stops = self._optimize_stop_order(vehicle, assigned_stops)
                for idx, stop in enumerate(ordered_stops):
                    stop.route = route
                    stop.sequence = idx + 1
                    stop.state = 'assigned'
                    stop.save()
                planned_routes.append(route)
        return planned_routes

    def _assign_stops_to_vehicle(self, vehicle, stops):
        # Asignar paradas según capacidad y proximidad (simplificado)
        assigned = []
        for stop in stops:
            if len(assigned) < vehicle.capacity:
                assigned.append(stop)
        for stop in assigned:
            stops.remove(stop)
        return assigned

    def _optimize_stop_order(self, vehicle, stops):
        # Algoritmo nearest neighbor para ordenar paradas
        if not stops:
            return []
        current_location = (vehicle.latitude, vehicle.longitude)
        ordered = []
        remaining = stops[:]
        while remaining:
            next_stop = min(remaining, key=lambda s: geodesic(current_location, (s.latitude, s.longitude)).km)
            ordered.append(next_stop)
            current_location = (next_stop.latitude, next_stop.longitude)
            remaining.remove(next_stop)
        return ordered 