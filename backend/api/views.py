from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import os
from .models import Chat, Message, RiwayatKonfigurasi, NetworkDevice, DeviceAlias
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.core.serializers import serialize
import base64
import ansible_runner
import subprocess
import json

SYSTEM_PROMPT = '''
You are a friendly and professional multi-vendor network configuration assistant.

Answer in Indonesian.

Your task is to generate ready-to-run CLI configurations for network devices such as MikroTik, Cisco, Huawei, Juniper, or Linux.



### STRICT SYNTAX RULES (CRITICAL):

You MUST check the target device vendor: {{ device_vendor }}.

1. **IF VENDOR IS HUAWEI (VRP/ATN):**
   - **DO NOT** use `system-view`, `quit`, or `return`. (Automation handles this).
   - Start directly with the configuration command (e.g., `interface ...`).
   - Enable interface: `undo shutdown` (NEVER use `no shutdown`).
   - Interface naming: Gunakan nama lengkap atau singkatan standar (e.g., `GigabitEthernet0/2/3`).
   - - [ATURAN PENTING KHUSUS ROUTER]: 
     Jika perangkat adalah ROUTER (bukan Switch) dan user meminta konfigurasi Layer 2 (Trunk/Access/Hybrid), 
     KAMU WAJIB MENULIS `portswitch` SEBELUM perintah `port link-type`.

2. **IF VENDOR IS CISCO (IOS):**
   - **DO NOT** use `configure terminal` or `exit`. (Automation handles this).
   - Start directly with the configuration command.
   - Enable interface: `no shutdown`.
   - Save config: `write memory`.

3. **IF VENDOR IS MIKROTIK:**
   - Use path-based commands (e.g., `/ip address add...`).
   - Do NOT use `system-view` or `conf t`.



⚙️ IMPORTANT RULE:



Use proper indentation to reflect the command hierarchy.



Example format (must be followed):

system-view

interface int g0/2/16

ip address 10.10.10.1 255.255.255.0

undo shutdown

quit



Do not include comments, descriptions, or contextual explanations.



Make sure the syntax matches the requested vendor (or automatically detect the vendor if not specified).



The output should be clean and executable directly on the target device.



Respond based on input context:



If the user greets you, respond with a short greeting in Indonesian.



If a configuration request is made, return only the appropriate configuration command.



If the user provides an interface or format example (e.g., "int g0/2/16"), use a similar pattern in the output.



You must always produce JSON in the following format:



You must always show on chatbot display in the following format:

Target: target_name,

Konfigurasi: config_cli



target_name must be taken from the device name mentioned in the user's input.



If the input does not contain a target name, you must ask the user to specify the device name.



config_cli must contain only the raw CLI commands, with no addi tional comments, explanations, or markdown formatting.



JIKA user mendeskripsikan topologi jaringan seperti koneksi antar perangkat (lewat teks atau gambar), KAMU WAJIB MENYERTAKAN blok JSON khusus untuk visualisasi graph.



FORMAT VISUALISASI GRAPH (Wajib gunakan blok code ```json_graph ... ```):

```json_graph

{

  "devices": [

    {"id": "Router1", "type": "router", "label": "Router Utama"},

    {"id": "Switch1", "type": "switch", "label": "Switch Lantai 1"}

  ],

  "connections": [

    {"source": "Router1", "target": "Switch1"}

  ]

}







'''

class ChatView(APIView):
    def post(self, request):
        print("Request Data:", request.data)
        
        # SETUP API KEY
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("CRITICAL: GROQ_API_KEY tidak ditemukan di .env")
            return Response({"error": "Server Config Error: API Key missing."}, status=500)

        user_message = request.data.get("prompt", "")
        uploaded_image = request.FILES.get("image")
        chat_id = request.data.get("chat_id")

        # Setup Chat Object
        if chat_id:
            chat = Chat.objects.filter(id=chat_id).first()
            if not chat:
                chat = Chat.objects.create(title="Percakapan Baru")
        else:
            chat = Chat.objects.create(title="Percakapan Baru")

        # =================================================================
        # ANALISIS GAMBAR (VISION) MENGGUNAKAN GROQ
        # =================================================================
        topology_json = None
        final_image_data = None

        if uploaded_image:
            print("Vision Mode Aktif (Groq Llama Vision)")
            try:
                uploaded_image.seek(0)
                image_bytes = uploaded_image.read()
                uploaded_image.seek(0) 

                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                mime_type = uploaded_image.content_type or "image/jpeg"
                final_image_data = f"data:{mime_type};base64,{base64_str}"


                model_vision = os.getenv("GROQ_MODEL_VISION", "meta-llama/llama-4-maverick-17b-128e-instruct")

                vision_payload = {
                    "model": model_vision,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": "Analisa topologi jaringan ini. Identifikasi perangkat (Router, Switch, PC) dan koneksinya secara detail. Output HANYA JSON raw tanpa markdown."
                                },
                                {
                                    "type": "image_url", 
                                    "image_url": {
                                        "url": final_image_data
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.1, 
                    "max_tokens": 1024
                }

                vision_resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=vision_payload
                )

                vision_data = vision_resp.json()

                if vision_resp.status_code != 200:
                    print(f"Groq Vision Error ({vision_resp.status_code}):", vision_data)
                    error_msg = vision_data.get('error', {}).get('message', 'Unknown Error')
                    return Response({"error": f"Vision AI Error: {error_msg}"}, status=500)

                if "choices" in vision_data:
                    vision_output = vision_data["choices"][0]["message"]["content"]
                    
                    clean_json = vision_output.replace("```json", "").replace("```", "").strip()
                    try:
                        topology_json = json.loads(clean_json)
                        chat.topology_data = topology_json
                        chat.save()
                        print("✅ Topology Data (Llama) saved to DB!")
                    except json.JSONDecodeError:
                        print("⚠️ Gagal parse JSON dari Llama Vision, menyimpan raw text.")
                        topology_json = {"raw": clean_json, "description": "Raw vision analysis"}
                else:
                    print("⚠️ Invalid Vision Response:", vision_data)

            except Exception as e:
                print(f"Exception Vision Block: {str(e)}")
                return Response({"error": f"Vision Process Failed: {str(e)}"}, status=500)

        # Menyimpan Pesan User ke DB
        if uploaded_image:
            Message.objects.create(chat=chat, role="user", content=user_message or "Uploaded Image", image=uploaded_image)
        elif user_message:
            Message.objects.create(chat=chat, role="user", content=user_message)




        if chat.title == "Percakapan Baru":
            if user_message:
                try:
                    title_payload = {
                        "model": "llama3-8b-8192", 
                        "messages": [
                            {"role": "system", "content": "Buat 3 hingga 5 kata singkat dalam bahasa indonesia yang merangkum perintah user. HANYA OUTPUTKAN JUDUL SAJA tanpa tanda kutip dan tanpa penjelasan."},
                            {"role": "user", "content": user_message}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 15
                    }
                    title_resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=title_payload
                    ).json()
                    
                    new_title = title_resp["choices"][0]["message"]["content"].strip().replace('"', '')
                    chat.title = new_title
                except Exception as e:
                    print(f"Gagal generate title: {e}")
                    kata_user = user_message.split()
                    chat.title = " ".join(kata_user[:4]) + ("..." if len(kata_user) > 4 else "")
            
            elif uploaded_image:
                 chat.title = "Analisis Topologi Gambar"
            
            chat.save()






        # =====================================================================================
        # GENERATE PROMPT UNTUK TEXT LLM
        # =====================================================================================
        if topology_json:
            groq_prompt = f"""
            User baru saja mengunggah gambar topologi jaringan.
            Berikut adalah hasil analisis Llama Vision terhadap gambar tersebut dalam format JSON:
            {json.dumps(topology_json, indent=2)}

            Instruksi User: "{user_message}"
            
            Tugasmu:
            1. Pahami topologi berdasarkan JSON di atas.
            2. Jawab instruksi user atau buatkan konfigurasi CLI jika diminta.
            3. Patuhi SYSTEM_PROMPT.
            """
        else:
            groq_prompt = user_message

        if not groq_prompt.strip():
             return Response({"reply": "Saya tidak dapat memproses permintaan kosong."}, status=200)

        # =====================================================================================
        # KIRIM KE GROQ (TEXT GENERATION)
        # =====================================================================================
        try:
            devices = NetworkDevice.objects.all()
            device_context_list = []
            for d in devices:
                device_context_list.append(f"- {d.name} : {d.vendor}")
            device_context_str = "\n".join(device_context_list)
            formatted_system_prompt = SYSTEM_PROMPT.replace("{device_context}", device_context_str)
            
            print(f"DEBUG: Context Injected -> \n{device_context_str}")
           
            # Mengambil history chat untuk konteks
            messages_in_chat = Message.objects.filter(chat=chat).order_by("timestamp")
            
            groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}] 
            
            for m in messages_in_chat:
                if m.content and m.content.strip():
                    groq_messages.append({"role": m.role, "content": m.content})

            groq_messages.append({"role": "user", "content": groq_prompt})


            model_text = os.getenv("GROQ_MODEL_TEXT", "openai/gpt-oss-120b") 

            text_payload = {
                "model": model_text,
                "messages": groq_messages,
                "temperature": 0.7 
            }

            groq_response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=text_payload
            )

            groq_data = groq_response.json()

            if "error" in groq_data:
                print("Groq Text API Error:", groq_data["error"])
                return Response({"error": f"Groq Text Error: {groq_data['error']['message']}"}, status=500)

            raw_reply = groq_data["choices"][0]["message"]["content"]

            # JSON GRAPH 
            final_reply_text = raw_reply
            extracted_topology = None

            if "```json_graph" in raw_reply:
                try:
                    parts = raw_reply.split("```json_graph")
                    if len(parts) > 1:
                        json_content = parts[1].split("```")[0].strip()
                        extracted_topology = json.loads(json_content)
                        final_reply_text = parts[0].strip()
                        print("Topology Graph extracted from Text Model!")
                except Exception as e:
                    print(f"Gagal parse JSON Graph: {e}")
                    final_reply_text = raw_reply

            topology_to_save = extracted_topology if extracted_topology else topology_json
            if topology_to_save:
                chat.topology_data = topology_to_save
                chat.save()

            # Simpan Jawaban Assistant
            Message.objects.create(chat=chat, role="assistant", content=final_reply_text)

            # Return response ke Frontend
            pesan = Message.objects.filter(chat=chat).order_by("timestamp")
            data_pesan = [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "text": m.content,
                    "image": m.image.url if m.image else None,
                    "timestamp": m.timestamp,
                }
                for m in pesan
            ]

            return Response({
                "chat_id": chat.id,
                "title": chat.title,
                "reply": final_reply_text,
                "messages": data_pesan,
                "topology": topology_to_save
            }, status=200)

        except Exception as e:
            print(f"Exception in Text Generation Block: {str(e)}")
            return Response({"error": f"Server Error (LLM): {str(e)}"}, status=500)




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
