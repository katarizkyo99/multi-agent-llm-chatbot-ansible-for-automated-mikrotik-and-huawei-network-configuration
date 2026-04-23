from django.db import models
import uuid

class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Percakapan Baru")
    topology_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tabel_chat" 

    def __str__(self):
        return self.title

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10) 
    content = models.TextField()
    image = models.ImageField(upload_to="chat_images/", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tabel_pesan"

    def __str__(self):
        return f"{self.role}: {self.content[:30] if self.content else '[image]'}"

class RiwayatKonfigurasi(models.Model):
    STATUS_CHOICES = (
        ("Disetujui", "Disetujui"),
        ("Ditolak", "Ditolak"),
    )

    config = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    image = models.ImageField(upload_to="riwayat_images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "riwayat_konfigurasi"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.status} - {self.created_at}"


class NetworkDevice(models.Model):
    name = models.CharField(max_length=100, unique=True)
    host = models.GenericIPAddressField()
    port = models.IntegerField(default=22)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    vendor = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class DeviceAlias(models.Model):
    alias_name = models.CharField(max_length=100, unique=True) 
    
    device = models.ForeignKey(
        NetworkDevice,
        on_delete=models.CASCADE,
        related_name='aliases'
    )
    
    def __str__(self):
        return f"{self.alias_name} -> {self.device.name}"
