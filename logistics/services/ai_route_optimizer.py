from logistics.models import DeliveryStop, Vehicle, DeliveryRoute
from django.utils import timezone
from geopy.distance import geodesic
import random

class AIRouteOptimizer:
    """
    Servicio de optimización de rutas usando clustering y nearest neighbor.
    Preparado para integración futura con modelos IA/ML avanzados.
    """
    def __init__(self, date=None):
        self.date = date or timezone.now().date()

    def optimize_routes(self, stops_queryset=None, vehicles_queryset=None):
        stops = list(stops_queryset or DeliveryStop.objects.filter(route__isnull=True, state='pending'))
        vehicles = list(vehicles_queryset or Vehicle.objects.filter(is_active=True))
        if not stops or not vehicles:
            return []
        # Clustering básico: asignar paradas cercanas a cada vehículo
        clusters = self._kmeans_clustering(stops, len(vehicles))
        planned_routes = []
        for idx, vehicle in enumerate(vehicles):
            assigned_stops = clusters.get(idx, [])
            if not assigned_stops:
                continue
            route = DeliveryRoute.objects.create(
                vehicle=vehicle,
                driver=vehicle.driver_set.first(),
                date=self.date,
                state='planned',
                optimized=True
            )
            ordered_stops = self._nearest_neighbor_order(vehicle, assigned_stops)
            for i, stop in enumerate(ordered_stops):
                stop.route = route
                stop.sequence = i + 1
                stop.state = 'assigned'
                stop.save()
            planned_routes.append(route)
        return planned_routes

    def _kmeans_clustering(self, stops, k):
        # Algoritmo K-means simple para agrupar paradas por proximidad
        if not stops or k <= 0:
            return {}
        # Inicializar centroides aleatorios
        centroids = random.sample([(s.latitude, s.longitude) for s in stops], min(k, len(stops)))
        clusters = {i: [] for i in range(k)}
        for _ in range(5):  # iteraciones
            # Asignar cada parada al centroide más cercano
            for s in stops:
                dists = [geodesic((s.latitude, s.longitude), c).km for c in centroids]
                idx = dists.index(min(dists))
                clusters[idx].append(s)
            # Recalcular centroides
            for i in range(k):
                if clusters[i]:
                    lat = sum(s.latitude for s in clusters[i]) / len(clusters[i])
                    lng = sum(s.longitude for s in clusters[i]) / len(clusters[i])
                    centroids[i] = (lat, lng)
        return clusters

    def _nearest_neighbor_order(self, vehicle, stops):
        # Ordenar paradas usando nearest neighbor desde la posición del vehículo
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