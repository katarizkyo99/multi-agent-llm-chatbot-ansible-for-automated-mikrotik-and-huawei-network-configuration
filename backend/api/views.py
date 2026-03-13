from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import os
import json
import base64
import subprocess
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import Chat, Message, RiwayatKonfigurasi, NetworkDevice, DeviceAlias

# ==============================================================================
# FUNGSI PEMBANTU UNTUK CALL API GROQ
# ==============================================================================
def call_groq_llm(api_key, model, messages, temperature=0.3):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048
    }
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload
    )
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"LLM Error ({resp.status_code}): {resp.text}")

# ==============================================================================
# SYSTEM PROMPTS 
# ==============================================================================

PROSES_1_PROMPT = """
Kamu adalah Network Architect & Assistant. Jawab dengan SINGKAT, padat, dan ramah murni dalam bahasa Indonesia.

DAFTAR PERANGKAT DI DATABASE SAAT INI (JANGAN DITAMPILKAN KECUALI DIMINTA USER):
{device_context}

ATURAN KERJA PROSES 1 (SANGAT PENTING):
1. JAWAB SINGKAT: Jawab tepat sesuai apa yang ditanyakan user saja.
2. ATURAN TABEL: JANGAN PERNAH menampilkan daftar perangkat di database kecuali diminta secara eksplisit.
3. TOPOLOGI MERMAID: Jika user meminta topologi, buatkan blok kode Markdown 'mermaid' (graph TD).
- CORRECT SYNTAX: `NodeA -->|ether1| NodeB`
- INCORRECT SYNTAX: `NodeA -->|ether1|> NodeB`
4. MENAMBAH PERANGKAT (STRICT RULE):
   Jika user ingin menambah perangkat baru, kamu WAJIB memastikan 6 data ini terkumpul:
   - name (Nama perangkat)
   - host (IP Address perangkat)
   - port (Port SSH, default 22)
   - username (Username SSH perangkat)
   - password (Password SSH perangkat)
   - vendor (WAJIB tawarkan pilihan: ketik 'routeros' untuk MikroTik, atau 'ce' untuk Huawei)
   JIKA ADA DATA YANG KURANG: Tanyakan secara spesifik data apa yang belum diisi.
   JIKA KE-6 DATA SUDAH LENGKAP: Kamu WAJIB berhenti bertanya dan hanya menambahkan satu baris teks tepat di akhir pesanmu dengan format murni seperti ini:
   [ADD_DEVICE_TO_DB] {"name": "...", "host": "...", "port": 22, "username": "...", "password": "...", "vendor": "..."}
5. PENUTUP PESAN: Di akhir pesan (kecuali saat proses menambah perangkat), cukup tawarkan: "Apakah Anda ingin saya buatkan konfigurasinya sekarang?".
6. EKSEKUSI KONFIGURASI: Jika user SETUJU untuk dikonfigurasi, KELUARKAN TAG: `[GENERATE_CONFIG]`.
7. MEMBACA PERANGKAT: Jika user meminta mengecek perangkat, KELUARKAN TAG: `[READ_DEVICE] nama_perangkat, perintah`.
"""
PROSES_2_PROMPT = """
You are a Multi-Vendor Network Engineer.
Your task is ONLY to generate raw CLI scripts that are ready to be executed based on chat history.

VENDOR RULES:

HUAWEI: DO NOT use system-view, quit, or return. Use undo shutdown. IF Layer 2 on the router, write portswitch.

CISCO: DO NOT use configure terminal or exit. Use no shutdown.

MIKROTIK: Use absolute paths (example: /ip address add...).

You must not greet or provide markdown explanations.
You MUST output in the following exact format:
Target: [Device Name from database]
IP: [Device IP Address from database]
Configuration:
[CLI command line]
[CLI command line]
"""


class ChatView(APIView):
   def post(self, request):
      api_key = os.getenv("GROQ_API_KEY")
      if not api_key:
         return Response({"error": "API Key missing."}, status=500)
         
      user_message = request.data.get("prompt", "")
      uploaded_image = request.FILES.get("image")
      chat_id = request.data.get("chat_id")
  
      chat = Chat.objects.filter(id=chat_id).first() if chat_id else Chat.objects.create(title="Percakapan Baru")
      
      # Simpan pesan user
      if uploaded_image:
          Message.objects.create(chat=chat, role="user", content=user_message or "Uploaded Image", image=uploaded_image)
      elif user_message:
          Message.objects.create(chat=chat, role="user", content=user_message)
  
      # Context Perangkat dari DB
      devices = NetworkDevice.objects.all()
      device_context = "| Nama Perangkat | IP Address | Vendor |\n|---|---|---|\n"
      for d in devices:
          device_context += f"| {d.name} | {d.host} | {d.vendor} |\n"
      formatted_proses_1_prompt = PROSES_1_PROMPT.replace("{device_context}", device_context)
  
      # History obrolan
      history = Message.objects.filter(chat=chat).order_by("timestamp")
      messages_for_llm = [{"role": "system", "content": formatted_proses_1_prompt}]
      for m in history:
          if m.content:
              messages_for_llm.append({"role": m.role, "content": m.content})
  
      try:
          # =================================================================
          # PROSES 1: VISION / TEXT ANALYZER
          # =================================================================
          proses_1_reply = ""
  
          if uploaded_image:
              print("▶️ Proses 1 (Vision) Bekerja...")
              uploaded_image.seek(0)
              image_bytes = uploaded_image.read()
              base64_str = base64.b64encode(image_bytes).decode('utf-8')
              final_image_data = f"data:{uploaded_image.content_type or 'image/jpeg'};base64,{base64_str}"
              
              vision_messages = [
                  {"role": "user", "content": [
                      {"type": "text", "text": "Analisis gambar topologi ini dan jelaskan perangkatnya. Buatkan juga format ```mermaid ... ``` nya."},
                      {"type": "image_url", "image_url": {"url": final_image_data}}
                  ]}
              ]
              
              proses_1_reply = call_groq_llm(
                  api_key=api_key, 
                  model="meta-llama/llama-4-scout-17b-16e-instruct", 
                  messages=vision_messages
              )
          else:
              print("▶️ Proses 1 (Text Analyzer) Bekerja...")
              proses_1_reply = call_groq_llm(
                  api_key=api_key, 
                  model="llama-3.3-70b-versatile", 
                  messages=messages_for_llm
              )
  
          final_bot_reply = proses_1_reply
  
          # =================================================================
          # ROUTING INTENT (Menangani hasil dari Proses 1)
          # =================================================================
          
          if "[GENERATE_CONFIG]" in proses_1_reply:
              print("▶️ User Setuju. Proses 2 (Configurator) Mengambil Alih...")
              
              messages_for_proses_2 = [
                  {"role": "system", "content": PROSES_2_PROMPT + f"\nContext Database:\n{device_context}"}
              ]
              for m in history:
                  if m.content:
                      messages_for_proses_2.append({"role": m.role, "content": m.content})
                      
              final_bot_reply = call_groq_llm(
                  api_key=api_key, 
                  model="openai/gpt-oss-120b", 
                  messages=messages_for_proses_2
              )
          
          # Melakukan monitoring / pengecekan
          elif "[READ_DEVICE]" in proses_1_reply:
              print("▶️ Intent: Membaca status perangkat...")
              final_bot_reply = "Saya sedang mengambil data langsung dari perangkat...\n\n" + proses_1_reply.replace("[READ_DEVICE]", "")
  
          # Menambahkan perangkatbaru ke DB
          
          elif "[ADD_DEVICE_TO_DB]" in proses_1_reply:
                print("▶️ Intent: Menambahkan perangkat ke DB...")
                try:
                    # Pisahkan teks balasan dengan tag JSON
                    parts = proses_1_reply.split("[ADD_DEVICE_TO_DB]")
                    bot_text = parts[0].strip()
                    json_str = parts[1].strip()
                    
                    # Bersihkan jika LLM iseng menambahkan backticks markdown (```json ... ```)
                    json_str = json_str.replace("```json", "").replace("```", "").strip()
                    
                    # Ubah string jadi dictionary
                    device_data = json.loads(json_str)
                    
                    # Simpan langsung ke database Django
                    NetworkDevice.objects.create(
                        name=device_data.get("name"),
                        host=device_data.get("host"),
                        port=int(device_data.get("port", 22)),
                        username=device_data.get("username"),
                        password=device_data.get("password"),
                        vendor=device_data.get("vendor").lower()
                    )
                    
                    final_bot_reply = bot_text + "\n\n✅ **Berhasil:** Perangkat telah ditambahkan ke database!"
                except Exception as e:
                    print(f"Gagal menyimpan perangkat: {e}")
                    final_bot_reply = proses_1_reply.split("[ADD_DEVICE_TO_DB]")[0].strip() + "\n\n❌ **Gagal:** Sistem tidak dapat menyimpan perangkat karena format data dari asisten tidak sesuai."
          # Simpan balasan final ke database
          Message.objects.create(chat=chat, role="assistant", content=final_bot_reply)
  
          # Return response
          pesan = Message.objects.filter(chat=chat).order_by("timestamp")
          data_pesan = [{"id": str(m.id), "role": m.role, "text": m.content, "timestamp": m.timestamp} for m in pesan]
  
          return Response({
              "chat_id": chat.id,
              "title": chat.title,
              "reply": final_bot_reply,
              "messages": data_pesan
          }, status=200)
  
      except Exception as e:
          print(f"Error in Multi-Agent Pipeline: {e}")
          return Response({"error": f"Server Error: {str(e)}"}, status=500)


@api_view(["GET"])
def get_chats(request):
    chats = Chat.objects.all().order_by("created_at")
    data = [
        {"id": str(c.id), "title": c.title, "created_at": c.created_at}
        for c in chats
    ]
    
    return JsonResponse(data, safe=False)


@api_view(["GET"])
def get_chat_messages(request, chat_id):
    
    messages = Message.objects.filter(chat_id=chat_id).order_by("timestamp")
    
    
    chat = Chat.objects.filter(id=chat_id).first()
    topology = chat.topology_data if chat else None

    msg_data = [
        {
            "id": str(m.id),
            "role": m.role,
            "text": m.content,
            "image": m.image.url if m.image else None,
            "timestamp": m.timestamp,
        }
        for m in messages
    ]
    
    
    return Response({
        "messages": msg_data,
        "topology": topology 
    })

@api_view(["POST"])
def create_chat(request):
    chat = Chat.objects.create(title="Percakapan Baru")
    return Response({"id": chat.id, "title": chat.title})


@api_view(["DELETE"])
def delete_chat(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
        chat.delete()
        return Response({"message": "Chat berhasil dihapus."})
    except Chat.DoesNotExist:
        return Response({"error": "Chat tidak ditemukan."}, status=404)


@api_view(["POST"])
def save_message(request):
    chat_id = request.data.get("chat_id")
    role = request.data.get("role")
    content = request.data.get("content")

    chat = Chat.objects.get(id=chat_id)

    msg = Message.objects.create(
        chat=chat,
        role=role,
        content=content
    )

    return Response({
        "message": "Message saved",
        "data": {
            "id": str(msg.id),
            "chat_id": str(chat_id),
            "role": msg.role,
            "content": msg.content
        }
    })



@api_view(["GET"])
def get_riwayat_konfigurasi(request):
    data = RiwayatKonfigurasi.objects.all()
    response_data = [
        {
            "config": item.config,
            "status": item.status,
            "created_at": item.created_at
        }
        for item in data
    ]
    return Response(response_data)

@api_view(["POST"])
def add_riwayat_konfigurasi(request):
    config = request.data.get("config")
    status = request.data.get("status")  

    if not config or not status:
        return Response({"error": "Data tidak lengkap"}, status=400)

    RiwayatKonfigurasi.objects.create(
        config=config,
        status=status
    )

    return Response({"message": "Riwayat disimpan"})



@api_view(["POST"])
def execute_config(request):
    try:
        print("=== RAW REQUEST DATA ===", request.data)
        
        # ==========================================
        # PARSING INPUT
        # ==========================================
        raw = request.data.get("config_cli", "")
        tasks = [] 
        
        current_target = None
        current_config = []

        lines = raw.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line: continue 

            if line.lower().startswith("target:"):
                if current_target and current_config:
                    tasks.append({
                        "target": current_target,
                        "config": "\n".join(current_config)
                    })
                    current_config = [] 
                current_target = line.split(":", 1)[1].strip().rstrip(",")
            
            elif line.lower().startswith("konfigurasi:"):
                content = line.split(":", 1)[1].strip()
                if content:
                    current_config.append(content)
            
            else:
                if current_target:
                    current_config.append(line)

        if current_target and current_config:
            tasks.append({
                "target": current_target,
                "config": "\n".join(current_config)
            })

        print(f"Ditemukan {len(tasks)} tugas konfigurasi.")

        if not tasks:
            return Response({"error": "Format input salah atau tidak ada target ditemukan."}, status=400)

        # ==========================================
        # EKSEKUSI ANSIBLE 
        # ==========================================
        final_results = []

        for i, task in enumerate(tasks):
            target_name_input = task['target']
            config_cli_input = task['config']
            
            print(f"\n[Task {i+1}/{len(tasks)}] Memproses: {target_name_input}")

            # LOGIKA PENCARIAN PERANGKAT 
            final_target_name = None
            try:
                alias_entry = DeviceAlias.objects.get(alias_name__iexact=target_name_input)
                final_target_name = alias_entry.device.name
                print(f" Ditemukan via Alias: {final_target_name}")
            except DeviceAlias.DoesNotExist:
                try:
                    # 2. Cek Direct
                    device_obj = NetworkDevice.objects.get(name__iexact=target_name_input)
                    final_target_name = device_obj.name
                    print(f" Ditemukan via Direct: {final_target_name}")
                except NetworkDevice.DoesNotExist:
                    # 3. Cek Fuzzy
                    clean_target = target_name_input.lower().replace(" ", "").replace("_", "").replace("-", "")
                    all_devices = NetworkDevice.objects.all()
                    for d in all_devices:
                        clean_db = d.name.lower().replace(" ", "").replace("_", "").replace("-", "")
                        if clean_db == clean_target:
                            final_target_name = d.name
                            print(f" Ditemukan via Fuzzy: {final_target_name}")
                            break
            
            if not final_target_name:
                err_msg = f" Gagal: Device '{target_name_input}' tidak ditemukan."
                print(err_msg)
                final_results.append({"target": target_name_input, "status": "failed", "error": err_msg})
                continue 

            # ANSIBLE
            try:
                device = NetworkDevice.objects.get(name=final_target_name)
                raw_lines = config_cli_input.splitlines()

                if device.vendor == 'ce':
                    cleaned_list = [
                        line.strip() for line in raw_lines 
                        if line.strip().lower() not in ['system-view', 'quit', 'return', 'sys', 'q']
                        and line.strip() != ""
                    ]
                    final_config_payload = "\n".join(cleaned_list)
                    print(f" Config Huawei: {final_config_payload}")
   
                else:
                   final_config_payload = [line.strip() for line in raw_lines if line.strip() != ""]
                   
                print(f"Payload tipe: {type(final_config_payload)}") 
                print(f"Payload isi: {final_config_payload}")  
               
                vars_file_path = f"/tmp/vars_{final_target_name.replace(' ', '_')}.json"

                with open(vars_file_path, "w") as vars_f:
                    json.dump({"config_cli": final_config_payload}, vars_f)

                inventory_file = f"/tmp/inventory_{final_target_name.replace(' ', '_')}.ini"
                
                safe_user = device.username.replace("\\", "\\\\") if device.username else "root"
                safe_pass = device.password.replace("\\", "\\\\") if device.password else ""
                safe_host = device.host.replace("\\", "\\\\")
                
                ansible_os = device.vendor

                with open(inventory_file, "w") as f:
                    f.write("[routers]\n")
                    f.write(f"{final_target_name.replace(' ', '_')} "
                            f"ansible_host={safe_host} "
                            f"ansible_user={safe_user} "
                            f"ansible_port={device.port} "
                            f"ansible_password='{safe_pass}' "
                            f"ansible_become=no "
                            f"ansible_network_os={ansible_os} "
                            f"ansible_connection=network_cli "
                            f"ansible_command_timeout=60 "
                            f"ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KexAlgorithms=+diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc,3des-cbc'\n")
                playbook_path = "/home/kyo/ta/ansible/apply_config.yml"   
                playbook_cmd = [
                    "ansible-playbook",
                    playbook_path,
                    "-i", inventory_file,
                    "-e", f"@{vars_file_path}"
                ]
       
                result = subprocess.run(
                    playbook_cmd,
                    env={**os.environ, "ANSIBLE_HOST_KEY_CHECKING": "False"},
                    capture_output=True,
                    text=True
                )

                print(f"\n{'='*20} ANSIBLE OUTPUT: {final_target_name} {'='*20}")
                print(">>> STDOUT (Output Normal):")
                print(result.stdout if result.stdout else "[KOSONG]")
                
                print("\n>>> STDERR (Error/Warning):")
                print(result.stderr if result.stderr else "[KOSONG]")
                print(f"{'='*60}\n")

                if os.path.exists(inventory_file):
                    os.remove(inventory_file)
                if os.path.exists(vars_file_path):
                    os.remove(vars_file_path)
             
                final_results.append({
                    "target": final_target_name,
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })

            except Exception as e:
                print(f"Error executing task for {final_target_name}: {e}")
                final_results.append({"target": final_target_name, "status": "exception", "error": str(e)})


        return Response({
            "message": f"Selesai memproses {len(tasks)} tugas.",
            "results": final_results
        }, status=200)

    except Exception as e:
        print("CRITICAL ERROR:", e)
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)




@api_view(["POST"])
def ping_device(request):
    ip = request.data.get("ip")

    if not ip:
        return Response({"error": "IP tidak diberikan"}, status=400)

    try:
        result = subprocess.run(
            ["ping", "-c", "4", ip],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return Response({
            "output": result.stdout,
            "success": (result.returncode == 0)
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["GET"])
def get_network_devices(request):
    try:
        devices = NetworkDevice.objects.all().order_by("name")
        
        response_data = [
            {
                "name": d.name,
                "device_category": d.vendor, 
                "ip_address": d.host 
            }
            for d in devices
        ]
        
        return Response(response_data, status=200)
    except Exception as e:
        print(f"Error fetching network devices: {str(e)}")
        return Response({"error": "Gagal mengambil data perangkat jaringan."}, status=500)
