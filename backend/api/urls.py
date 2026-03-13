from django.urls import path
from .views import (
    ChatView, get_chats, get_chat_messages, create_chat, delete_chat,
    get_riwayat_konfigurasi, add_riwayat_konfigurasi, save_message, 
    execute_config, ping_device, get_network_devices, delete_riwayat_konfigurasi, 
    delete_all_riwayat
)
urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('chats/', get_chats, name='get_chats'),
    path('chats/<uuid:chat_id>/messages/', get_chat_messages, name='get_chat_messages'),
    path("chats/create/", create_chat, name="create_chat"),
    path("chats/<uuid:chat_id>/delete/", delete_chat, name="delete_chat"),
    path("riwayat-konfigurasi/", get_riwayat_konfigurasi),
    path("riwayat-konfigurasi/add/", add_riwayat_konfigurasi),
    path("riwayat-konfigurasi/<int:riwayat_id>/delete/", delete_riwayat_konfigurasi),
    path("riwayat-konfigurasi/delete-all/", delete_all_riwayat),
    path("chats/messages/save/", save_message, name="save_message"),
    path('execute_config/', execute_config),
    path("ping/", ping_device, name="ping_device"),
    path('network-devices/', get_network_devices, name='get_network_devices'),
]


