from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    role = models.CharField(max_length=50, null=True, default='user')
    pass
    def __str__(self):
        return self.username


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ServiceCenter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True)
    center_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True, blank=True, null=True)
    location = models.CharField(null=True)
    services_offered = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Suspended', 'Suspended')],
        default='Pending'
    )
    rating_avg = models.FloatField(default=0.0)

    def __str__(self):
        return self.center_name


class ServicePrice(models.Model):
    center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('center', 'service')

    def __str__(self):
        return f"{self.center.center_name} - {self.service.name}: ${self.price}"



class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=100)
    booking_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Booked', 'Booked'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')],
        default='Pending'
    )

    def __str__(self):
        return f"Booking {self.id} - {self.service_type}"



class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.id} - {self.rating}"



class EmergencyRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE, null=True)
    location = models.CharField(null=True)
    emergency_type = models.CharField(max_length=100)
    request_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected'), ('Completed', 'Completed')],
        default='Pending'
    )

    def __str__(self):
        return f"Emergency {self.id} - {self.emergency_type}"
