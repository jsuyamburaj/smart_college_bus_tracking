// Driver GPS Tracking Module

class DriverGPS {
    constructor(busId, updateInterval = 10000) {
        this.busId = busId;
        this.updateInterval = updateInterval;
        this.watchId = null;
        this.lastLocation = null;
        this.socket = null;
        this.isTracking = false;
        
        this.init();
    }
    
    init() {
        this.setupWebSocket();
        this.setupEventListeners();
    }
    
    setupWebSocket() {
        // Connect to WebSocket for real-time updates
        this.socket = new WebSocket(`ws://${window.location.host}/ws/tracking/bus/${this.busId}/`);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.isTracking = true;
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.isTracking = false;
            // Try to reconnect after 5 seconds
            setTimeout(() => this.setupWebSocket(), 5000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    setupEventListeners() {
        // Start tracking button
        document.getElementById('startTracking')?.addEventListener('click', () => this.startTracking());
        
        // Stop tracking button
        document.getElementById('stopTracking')?.addEventListener('click', () => this.stopTracking());
        
        // Manual location update
        document.getElementById('updateLocation')?.addEventListener('click', () => this.getCurrentLocation());
        
        // Trip control buttons
        document.getElementById('startTrip')?.addEventListener('click', () => this.startTrip());
        document.getElementById('endTrip')?.addEventListener('click', () => this.endTrip());
        
        // Report issue
        document.getElementById('reportIssue')?.addEventListener('click', () => this.reportIssue());
    }
    
    startTracking() {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser');
            return;
        }
        
        const options = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        };
        
        this.watchId = navigator.geolocation.watchPosition(
            (position) => this.handlePositionUpdate(position),
            (error) => this.handleGeolocationError(error),
            options
        );
        
        this.isTracking = true;
        this.showNotification('Tracking started', 'success');
    }
    
    stopTracking() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        
        this.isTracking = false;
        this.showNotification('Tracking stopped', 'warning');
    }
    
    getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.handlePositionUpdate(position);
                    resolve(position);
                },
                (error) => {
                    this.handleGeolocationError(error);
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }
    
    handlePositionUpdate(position) {
        const { latitude, longitude, speed, accuracy } = position.coords;
        const timestamp = new Date().toISOString();
        
        // Update UI
        this.updateLocationDisplay(latitude, longitude, speed);
        
        // Update map marker
        this.updateMapMarker(latitude, longitude);
        
        // Send to server
        this.sendLocationToServer({
            latitude,
            longitude,
            speed: speed ? speed * 3.6 : 0, // Convert m/s to km/h
            accuracy,
            timestamp
        });
        
        // Check geofences
        this.checkGeofences(latitude, longitude);
        
        this.lastLocation = { latitude, longitude, timestamp };
    }
    
    updateLocationDisplay(lat, lng, speed) {
        // Update location display
        const locationElement = document.getElementById('currentLocation');
        if (locationElement) {
            locationElement.innerHTML = `
                <strong>Lat:</strong> ${lat.toFixed(6)}<br>
                <strong>Lng:</strong> ${lng.toFixed(6)}
            `;
        }
        
        // Update speed display
        const speedElement = document.getElementById('currentSpeed');
        if (speedElement) {
            const speedKmh = speed ? Math.round(speed * 3.6) : 0;
            speedElement.textContent = speedKmh;
            
            // Update speed color based on value
            if (speedKmh > 80) {
                speedElement.style.color = '#f72585'; // Danger
            } else if (speedKmh > 60) {
                speedElement.style.color = '#f8961e'; // Warning
            } else {
                speedElement.style.color = '#4cc9f0'; // Normal
            }
        }
        
        // Update last update time
        const timeElement = document.getElementById('lastUpdateTime');
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString();
        }
    }
    
    updateMapMarker(lat, lng) {
        // This function should be implemented based on your map library
        if (window.busMarker && window.map) {
            window.busMarker.setLatLng([lat, lng]);
            window.map.panTo([lat, lng]);
        }
    }
    
    async sendLocationToServer(locationData) {
        try {
            const response = await fetch(`/tracking/update-location/${this.busId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(locationData)
            });
            
            const data = await response.json();
            
            if (!data.success) {
                console.error('Failed to update location:', data.error);
                this.showNotification('Failed to update location', 'danger');
            }
        } catch (error) {
            console.error('Error sending location:', error);
            this.showNotification('Network error. Location not saved.', 'danger');
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'location_update':
                // Another device updated location
                this.handleRemoteLocationUpdate(data.data);
                break;
                
            case 'status_update':
                this.handleStatusUpdate(data.data);
                break;
                
            case 'notification':
                this.showNotification(data.data.message, data.data.type);
                break;
                
            case 'command':
                this.handleCommand(data.data);
                break;
        }
    }
    
    handleRemoteLocationUpdate(locationData) {
        // Update UI with remote location
        if (locationData.bus_id === this.busId) {
            this.updateMapMarker(locationData.latitude, locationData.longitude);
        }
    }
    
    handleStatusUpdate(statusData) {
        // Update bus status display
        const statusElement = document.getElementById('busStatus');
        if (statusElement) {
            statusElement.textContent = statusData.status;
            statusElement.className = `badge bg-${this.getStatusColor(statusData.status)}`;
        }
    }
    
    handleCommand(commandData) {
        switch (commandData.action) {
            case 'start_trip':
                this.startTrip();
                break;
                
            case 'end_trip':
                this.endTrip();
                break;
                
            case 'emergency_stop':
                this.emergencyStop();
                break;
        }
    }
    
    async startTrip() {
        try {
            const response = await fetch(`/api/trips/start/${this.busId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Trip started successfully', 'success');
                this.startTracking();
            } else {
                this.showNotification(data.error, 'danger');
            }
        } catch (error) {
            console.error('Error starting trip:', error);
            this.showNotification('Failed to start trip', 'danger');
        }
    }
    
    async endTrip() {
        try {
            const response = await fetch(`/api/trips/end/${this.busId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Trip ended successfully', 'success');
                this.stopTracking();
            } else {
                this.showNotification(data.error, 'danger');
            }
        } catch (error) {
            console.error('Error ending trip:', error);
            this.showNotification('Failed to end trip', 'danger');
        }
    }
    
    async reportIssue() {
        const issue = prompt('Please describe the issue:');
        
        if (!issue) return;
        
        try {
            const response = await fetch('/api/issues/report/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    bus_id: this.busId,
                    issue: issue,
                    location: this.lastLocation
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Issue reported successfully', 'success');
            } else {
                this.showNotification(data.error, 'danger');
            }
        } catch (error) {
            console.error('Error reporting issue:', error);
            this.showNotification('Failed to report issue', 'danger');
        }
    }
    
    emergencyStop() {
        this.stopTracking();
        this.showNotification('EMERGENCY STOP ACTIVATED', 'danger', true);
        
        // Send emergency notification
        fetch('/api/emergency/stop/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                bus_id: this.busId,
                location: this.lastLocation,
                reason: 'emergency_stop'
            })
        });
    }
    
    checkGeofences(lat, lng) {
        // Check if current location is inside any geofence
        fetch(`/api/geofences/check/?lat=${lat}&lng=${lng}&bus_id=${this.busId}`)
            .then(response => response.json())
            .then(data => {
                if (data.inside_geofence) {
                    this.showNotification(`Entered ${data.geofence_name}`, 'info');
                }
            })
            .catch(error => console.error('Error checking geofences:', error));
    }
    
    handleGeolocationError(error) {
        let message = '';
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                message = 'Location permission denied. Please enable location services.';
                break;
            case error.POSITION_UNAVAILABLE:
                message = 'Location information unavailable.';
                break;
            case error.TIMEOUT:
                message = 'Location request timed out.';
                break;
            default:
                message = 'Unknown error occurred.';
                break;
        }
        
        this.showNotification(message, 'danger');
    }
    
    showNotification(message, type = 'info', persistent = false) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            ${persistent ? '' : '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'}
        `;
        
        // Add to notification container
        const container = document.getElementById('notificationContainer') || 
                         this.createNotificationContainer();
        
        container.appendChild(notification);
        
        // Auto remove after 5 seconds if not persistent
        if (!persistent) {
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    }
    
    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notificationContainer';
        container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            max-width: 350px;
        `;
        
        document.body.appendChild(container);
        return container;
    }
    
    getStatusColor(status) {
        const colors = {
            'active': 'success',
            'inactive': 'secondary',
            'maintenance': 'warning',
            'emergency': 'danger'
        };
        
        return colors[status] || 'secondary';
    }
    
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        return cookieValue;
    }
    
    // Cleanup
    destroy() {
        this.stopTracking();
        
        if (this.socket) {
            this.socket.close();
        }
        
        // Clear any intervals
        clearInterval(this.updateInterval);
    }
}

// Initialize driver GPS when page loads
document.addEventListener('DOMContentLoaded', () => {
    const busId = document.body.dataset.busId;
    
    if (busId) {
        window.driverGPS = new DriverGPS(busId);
    }
});