from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


admin.site.register(User, UserAdmin)
admin.site.register(ServiceCenter)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(EmergencyRequest)