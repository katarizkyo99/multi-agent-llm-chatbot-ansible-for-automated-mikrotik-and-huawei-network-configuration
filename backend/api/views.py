from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import os
import json
import base64
import subprocess
import re
import time
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
# FUNGSI UNTUK MEMBERSIHKAN SINTAKS MERMAID YANG DIHASILKAN LLM
# ==============================================================================
def sanitize_mermaid(text):
    import re
    def fix_newlines(match):
        inner = match.group(1).replace('\n', '<br>').replace('\\n', '<br>')
        return f'[{inner}]'
        
    text = re.sub(r'\[(.*?)\]', fix_newlines, text, flags=re.DOTALL)

    cleaned_lines = []
    for line in text.split('\n'):
        
        def clean_node(match):
            node_id = match.group(1).strip()
            content = match.group(2).replace('"', '').strip()
            return f'{node_id}["{content}"]'

        line = re.sub(r'([a-zA-Z0-9_]+)\s*\[(.*?)\]', clean_node, line)
        
        line = re.sub(r'-\.[^>]*>', '-->', line)
        line = re.sub(r'-{2,}>+', '-->', line)
        line = re.sub(r'<+-{2,}>*', '-->', line)
        
        def clean_edge(match):
            arrow = "-->" 
            label = match.group(2).replace('"', '').replace("(", "").replace(")", "").replace(">", "").replace("<", "").strip()
            return f"{arrow}|{label}|"
            
        line = re.sub(r'(-->|---)\|([^|]+)\|', clean_edge, line)    
        line = re.sub(r'(-->|---)\|[^|]*$', r'\1', line)
        
        cleaned_lines.append(line)
        
    return '\n'.join(cleaned_lines)




# =================================================================
# CONFIGURATOR
# =================================================================  
def configurator(preview_text, device_context):
    results = []            
    # Split berdasarkan ### device
    sections = re.split(r'#+\s*', preview_text)

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        lines = sec.splitlines()            
        device_name = lines[0].strip()            
        config_lines = []

        for line in lines[1:]:
            line = line.strip()

            if not line:
                continue            
            if "Execute this now?" in line:
                continue           
            config_lines.append(line)

        # Cari IP dari DB context
        ip_address = "UNKNOWN"
        for d in NetworkDevice.objects.all():
            if d.name.lower() == device_name.lower():
                ip_address = d.host
                break

        result_block = (
            f"Target: {device_name}\n"
            f"IP Address: {ip_address}\n"
            f"Konfigurasi:\n"
            + "\n".join(config_lines)
        )

        results.append(result_block)       
    return "\n\n".join(results)
          

# ==============================================================================
# SYSTEM PROMPTS 
# ==============================================================================
SHARED_VENDOR_RULES = """
[GLOBAL]
- Pure text output only.
- Follow topology strictly.
- Never configure devices not mentioned in topology/request.
- Ping max 5 packets only.
- Keep responses concise.

[HUAWEI]
- Use `quit`, never `return` or `!`.
- Use `undo shutdown` to enable interfaces.
- Create VLAN globally first.
- Exit interface before `undo vlan`.
- OSPF uses wildcard masks.
- DHCP order:
  1. dhcp enable
  2. ip pool
  3. vlan
  4. vlanif
  5. dhcp select global

[MIKROTIK]
- Use absolute paths only.
- VLAN uses `/interface vlan add`.
- Never use `/ip vlan`.
- Never invent bridge/interface names.
- NAT only if explicitly requested.
- OSPF uses RouterOS v6 syntax.
- DHCP order:
  1. /ip pool add
  2. /ip dhcp-server add
  3. /ip dhcp-server network add
"""

PROSES_1_PROMPT = """
Role: NetArch.
Speak concise Indonesian.
Database:{device_context}
""" + SHARED_VENDOR_RULES + """

ACTIONS:
- Add device:
[ADD_DEVICE_TO_DB] {...}

- Delete device:
[DELETE_DEVICE_FROM_DB] {...}

- Read device:
[READ_DEVICE] device_name, command

RULES:
- If topology detected, generate Mermaid graph.
- For configuration requests, output preview config blocks using:
### DEVICE_NAME

- Never execute automatically.
- Only output [GENERATE_CONFIG] if user confirms briefly:
ya/gas/execute/run

- Always use [READ_DEVICE] for live device checks.
- Reject unrelated topics.

If rejecting:
"Maaf, saya hanya membantu konfigurasi jaringan, topologi, dan manajemen perangkat."
"""

# ==============================================================================
# PIPELINE CHATBOT 
# ==============================================================================
class ChatView(APIView):
   def post(self, request):
      start_time = time.time()
      llm_text_time = 0.0   
      llm_vision_time = 0.0
      ansible_time = 0.0
      api_key = os.getenv("GROQ_API_KEY")
      if not api_key:
         return Response({"error": "API Key missing."}, status=500)
      
         
      user_message = request.data.get("prompt", "")
      uploaded_image = request.FILES.get("image")
      chat_id = request.data.get("chat_id") 
       
      # Mengambil chat / membuat percakapan baru
      chat = Chat.objects.filter(id=chat_id).first() if chat_id else Chat.objects.create(title="Percakapan Baru")
       
    
      # Menyimpan pesan user
      if uploaded_image:
          Message.objects.create(chat=chat, role="user", content=user_message or "Uploaded Image", image=uploaded_image)
      elif user_message:
          Message.objects.create(chat=chat, role="user", content=user_message)

      # Membuat Judul Otomatis
      if chat.title == "Percakapan Baru":
            if user_message:
                try:
                    print("Membuat judul obrolan...")
                    title_messages = [
                        {"role": "system", "content": "Create 3 to 5 short words in Indonesian that summarize the user's command. ONLY OUTPUT THE TITLE without quotation marks, explanations, or markdown."},
                        {"role": "user", "content": user_message}
                    ]
                    new_title = call_groq_llm(api_key, "llama-3.1-8b-instant", title_messages, temperature=0.3)
                    
                    chat.title = new_title.replace('"', '').replace('*', '').strip()
                except Exception as e:
                    print(f"Gagal membuat judul: {e}")
                    kata_user = user_message.split()
                    chat.title = " ".join(kata_user[:4]) + ("..." if len(kata_user) > 4 else "")
            elif uploaded_image:
                chat.title = "Analisis Topologi Gambar"
            
            chat.save()

       
      # Membuat Konteks dari DB dan History Chat
      devices = NetworkDevice.objects.all()
      device_context = "| Nama Perangkat | IP Address | Vendor |\n|---|---|---|\n"
      for d in devices:
          device_context += f"| {d.name} | {d.host} | {d.vendor} |\n"

      memori_topologi = f"\n\n[TOPOLOGI ROOM INI]:\n{chat.topology_data}\n(Use the IP and Interface data from the text above for configuration. DO NOT ask the user again.)" if chat.topology_data else ""
      formatted_proses_1_prompt = PROSES_1_PROMPT.replace("{device_context}", device_context) + memori_topologi
  
      # Mengambil 10 pesan terakhir untuk konteks LLM
      raw_history = Message.objects.filter(chat=chat).order_by("timestamp")
      history = list(raw_history)[-6:]
      messages_for_llm = [{"role": "system", "content": formatted_proses_1_prompt}]
      for m in history:
          if m.content:
              messages_for_llm.append({"role": m.role, "content": m.content})
  
      try:
          # =================================================================
          # PROSES 1: GAMBAR / TEXT ANALYZER
          # =================================================================
          proses_1_reply = ""
          # Proses Gambar
          if uploaded_image:
              print(" Proses 1 (Vision) Bekerja...")
              
              uploaded_image.seek(0)
              image_bytes = uploaded_image.read()
              base64_str = base64.b64encode(image_bytes).decode('utf-8')
              final_image_data = f"data:{uploaded_image.content_type or 'image/jpeg'};base64,{base64_str}"

              vision_messages = [
                  {"role": "user", "content": [
                      {"type": "text", "text": "Analyze this topology image. Output EXACTLY in this format:\n\n**Analisis:**\n[WRITE IN INDONESIAN: Explain in detail which device connects to which device via which interface. Include IPs and vendors]\n\n**Gambar Topologi:**\n```mermaid\ngraph TD\nA[\"Name (Vendor)<br>IP\"] -->|Interface| B[\"Name (Vendor)<br>IP\"]\n```\nRULES:\n1. Node IDs MUST be single letters/words with NO SPACES (e.g., use A, B, R1, SW1).\n2. STRICT: You MUST use brackets [\"...\"] for nodes. NEVER use parentheses ().\n3. Use <br> in nodes for line breaks. NEVER use physical newlines (Enter) inside brackets.\n4. Put interface names on edges (e.g., -->|G0/0|).\n5. ONLY ONE mermaid block. No yapping."},
                      {"type": "image_url", "image_url": {"url": final_image_data}}
                  ]}
              ]
                
              t0_vision = time.time()
              
              proses_1_reply = call_groq_llm(
                  api_key=api_key, 
                  model="meta-llama/llama-4-scout-17b-16e-instruct", 
                  messages=vision_messages
              )
              
              llm_vision_time += (time.time() - t0_vision)
              
              chat.topology_data = proses_1_reply
              chat.save()
          else:
              # Proses Teks
              print(" Proses 1 (Text Analyzer) Bekerja...")             
              
              t0_text = time.time()
              
              proses_1_reply = call_groq_llm(
                  api_key=api_key, 
                  model="llama-3.3-70b-versatile", #openai/gpt-oss-120b #llama-3.3-70b-versatile
                  messages=messages_for_llm,
                  temperature = 0.1
              )
              llm_text_time += (time.time() - t0_text)

          final_bot_reply = sanitize_mermaid(proses_1_reply)
            
          proses_1_reply = final_bot_reply


          if "```mermaid" in proses_1_reply or "Analisis:" in proses_1_reply:
              chat.topology_data = proses_1_reply
              chat.save()
              print("Memori topologi berhasil dikunci untuk Room ini.")
              
          # =================================================================
          # ROUTING INTENT
          # =================================================================
          clean_reply = proses_1_reply.strip()
          confirm_words = [
              "ya",
              "y",
              "yes",
              "gas",
              "run",
              "execute",
              "lanjut",
              "oke",
              "ok",
              "apply"
          ]
        
          is_short_confirm = (
              user_message.strip().lower() in confirm_words
          )
        
          if clean_reply == "[GENERATE_CONFIG]" and is_short_confirm:
                print("User Setuju. Configurator Mengambil Alih...")
                last_preview = ""
            
                for m in reversed(history):
                    if (
                        m.role == "assistant" 
                        and m.content
                        and "Execute this now?" in m.content
                        ):
                        last_preview = m.content
                        break
            
                if not last_preview:
                    final_bot_reply = "Preview konfigurasi tidak ditemukan."

            
                final_bot_reply = configurator(
                    last_preview,
                    device_context
                )


          elif clean_reply == "[GENERATE_CONFIG]" and not is_short_confirm:        
              print("Memblokir eksekusi otomatis karena prompt user panjang.")        
              final_bot_reply = ("Eksekusi dibatalkan karena konfirmasi tidak valid.")

         # Membaca status/konfigurasi perangkat jaringan
          elif clean_reply.startswith("[READ_DEVICE]"):
              print("Membaca status perangkat...")
              try:
                  # Parsing
                  raw_intent = proses_1_reply.replace("[READ_DEVICE]", "").strip()
                  parts = raw_intent.split(",", 1)
                  
                  if len(parts) == 2:
                      target_device = parts[0].strip(' "\'')
                      target_command = parts[1].strip(' "\'')

                      t0_ansible = time.time()
                      # Memanggil fungsi eksekutor Ansible Read
                      ansible_output = execute_read_device(
                          target_device, 
                          target_command)

                      ansible_time += (time.time() - t0_ansible)
                      
                      if "❌" in ansible_output or "Gagal" in ansible_output:
                          final_bot_reply = ansible_output
                      else:
                          print(" Memformat output raw menjadi rapi...")
                          format_messages = [
                              {"role": "system", 
                               "content": (
                                      "Format raw network CLI output.\n"
                                      "1. Multi-column/list -> Markdown table.\n"
                                      "2. Single-line -> text block.\n"
                                      "3. Output ONLY formatted result."
                                  )
                              },
                              {"role": "user", "content": ansible_output}
                          ]
                          
                          try:
                              table_output = call_groq_llm(api_key, 
                                                           "llama-3.1-8b-instant", 
                                                           format_messages, 
                                                           temperature=0.1)
                              
                              final_bot_reply = (
                                  f" **Data Perangkat {target_device}**\n"
                                  f"- **Perintah:** `{target_command}`\n\n"
                                  f"{table_output}"
                              )
                          except Exception:
                              final_bot_reply = (
                                  f" **Data Perangkat {target_device}**\n"
                                  f"- **Perintah:** `{target_command}`\n\n"
                                  f"```text\n{ansible_output}\n```"
                              )
                  else:
                      final_bot_reply = " Maaf, asisten gagal memformat perintah baca perangkat."
                      
              except Exception as e:
                  final_bot_reply = f"Gagal memproses perintah baca: {str(e)}"
          
  
          # Menambahkan perangkat baru ke DB
          elif clean_reply.startswith("[ADD_DEVICE_TO_DB]"):
                print("Menambahkan perangkat ke DB...")
                try:
                    parts = clean_reply.split("[ADD_DEVICE_TO_DB]")
                    raw_json_str = parts[1].strip()
                    
                    json_match = re.search(
                        r'\{.*\}', 
                        raw_json_str, 
                        re.DOTALL)
                    
                    if not json_match:
                        raise ValueError("Format JSON tidak ditemukan.")
                    
                    clean_json = json_match.group(0)
                    device_data = json.loads(clean_json)
                    
                    raw_ip = device_data.get("host", "")
                    clean_ip = raw_ip.split('/')[0].strip()
                    
                    NetworkDevice.objects.update_or_create(
                        name=device_data.get("name"), 
                        defaults={
                            "host": clean_ip,
                            "port": int(device_data.get("port")),
                            "username": device_data.get("username"),
                            "password": device_data.get("password"),
                            "vendor": device_data.get("vendor").lower()
                        }
                    )
                    
                    final_bot_reply = ("Berhasil: perangkat ditambahkan ke database.")
                    
                except Exception as e:
                    final_bot_reply = (f"Gagal menyimpan perangkat: {str(e)}")

          # Menghapus Perangkat  
          elif clean_reply.startswith("[DELETE_DEVICE_FROM_DB]"):
                print("Menghapus perangkat dari DB...")
                try:
                    parts = clean_reply.split("[DELETE_DEVICE_FROM_DB]")
                    raw_json_str = parts[1].strip()
                    
                    json_match = re.search(
                        r'\{.*\}', 
                        raw_json_str, 
                        re.DOTALL)
                    
                    if not json_match:
                        raise ValueError("Format JSON tidak ditemukan.")
                    
                    clean_json = json_match.group(0)
                    device_data = json.loads(clean_json)
                    device_name = device_data.get("name", "").strip()   
                    deleted_count, _ = (
                        NetworkDevice.objects.filter(name__iexact=device_name).delete())
                    
                    if deleted_count > 0:
                        final_bot_reply = (f"\n\n **Berhasil:** Perangkat '{device_name}' telah dihapus dari database.")
                    else:
                        final_bot_reply = (f"\n\n **Perhatian:** Perangkat '{device_name}' tidak ditemukan di database. Pastikan namanya diketik dengan benar.")
                        
                except Exception as e:
                    final_bot_reply = (f"Gagal menghapus perangkat: {str(e)}")
          
          # Penyimpanan Pesan ke DB dan Pemrosesan Respons Final
          Message.objects.create(chat=chat, role="assistant", content=final_bot_reply)
  
          pesan = Message.objects.filter(chat=chat).order_by("timestamp")
          data_pesan = [{"id": str(m.id), "role": m.role, "text": m.content, "timestamp": m.timestamp} for m in pesan]

          end_time = time.time()
          execution_time = end_time - start_time

          print(f"\n{'='*40}")
          print(f"[LOG PENGUJIAN] DETAIL WAKTU EKSEKUSI")
          print(f"{'='*40}")
          print(f"Waktu Respons LLM (Vision) : {llm_vision_time:.3f} detik")
          print(f"Waktu Respons LLM (Teks)   : {llm_text_time:.3f} detik")
          print(f"Waktu Eksekusi Ansible     : {ansible_time:.3f} detik")
          print(f"Total Waktu Siklus Sistem  : {execution_time:.3f} detik")
          print(f"{'='*40}\n")
          
          return Response({
              "chat_id": chat.id,
              "title": chat.title,
              "reply": final_bot_reply,
              "messages": data_pesan
          }, status=200)
  
      except Exception as e:
          print(f"Error in Multi-Agent Pipeline: {e}")
          return Response({"error": f"Server Error: {str(e)}"}, status=500)

# ==============================================================================
# SECTION 4: CRUD CHAT DAN PESAN
# ==============================================================================

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

# Manajemen Riwayat Konfigurasi
@api_view(["GET"])
def get_riwayat_konfigurasi(request):
    data = RiwayatKonfigurasi.objects.all().order_by("-created_at")
    response_data = [
        {
            "id": item.id,
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

@api_view(["DELETE"])
def delete_riwayat_konfigurasi(request, riwayat_id):
    try:
        item = RiwayatKonfigurasi.objects.get(id=riwayat_id)
        item.delete()
        return Response({"message": "Riwayat berhasil dihapus."})
    except RiwayatKonfigurasi.DoesNotExist:
        return Response({"error": "Data tidak ditemukan."}, status=404)

@api_view(["DELETE"])
def delete_all_riwayat(request):
    RiwayatKonfigurasi.objects.all().delete()
    return Response({"message": "Semua riwayat berhasil dihapus."})


# Eksekusi Ansible
@api_view(["POST"])
def execute_config(request):
    try:
        print("=== RAW REQUEST DATA ===", request.data)
        # Parsing Input dari Frontend untuk Memisahkan mana yang "Target" dan mana yang "Konfigurasi"
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
        # EKSEKUSI TASK ANSIBLE 
        # ==========================================
        final_results = []

        for i, task in enumerate(tasks):
            target_name_input = task['target']
            config_cli_input = task['config']
            
            print(f"\n[Task {i+1}/{len(tasks)}] Memproses: {target_name_input}")

            # LOGIKA PENCARIAN TARGET PERANGKAT 
            final_target_name = None
            try:
                # Cari Via Alias
                alias_entry = DeviceAlias.objects.get(alias_name__iexact=target_name_input)
                final_target_name = alias_entry.device.name
                print(f" Ditemukan via Alias: {final_target_name}")
            except DeviceAlias.DoesNotExist:
                try:
                    # Cari Via Direct
                    device_obj = NetworkDevice.objects.get(name__iexact=target_name_input)
                    final_target_name = device_obj.name
                    print(f" Ditemukan via Direct: {final_target_name}")
                except NetworkDevice.DoesNotExist:
                    # 3. Cari Via Fuzzy
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

            # Eksekusi Playbook Ansible
            try:
                device = NetworkDevice.objects.get(name=final_target_name)
                raw_lines = config_cli_input.splitlines()

                # Cleaning CLI untuk Vendor Huawei
                if device.vendor.lower() in ['ce', 'vrp']:
                    cleaned_list = [
                        line.strip() for line in raw_lines 
                        if line.strip().lower() not in ['system-view', 'quit', 'return', 'sys', 'q']
                        and line.strip() != ""
                        and not line.strip().lower().startswith("ip address:")
                        and not ":" in line.strip()
                    ]
                    final_config_payload = "\n".join(cleaned_list)
                    print(f" Config Huawei : {final_config_payload}")
   
                else:
                   cleaned_list = [
                       line.strip() for line in raw_lines 
                       if line.strip() != ""
                       and not line.strip().lower().startswith("ip address:")
                       and not line.strip().lower().startswith("target:")
                   ]
                   final_config_payload = " ; ".join(cleaned_list)
                   print(f" Config MikroTik : {final_config_payload}")
                   
                print(f"Payload tipe: {type(final_config_payload)}") 
                print(f"Payload isi: {final_config_payload}")  

                # Pembuatan File Temporary untuk Variabel dan Inventory
                vars_file_path = f"/tmp/vars_{final_target_name.replace(' ', '_')}.json"

                with open(vars_file_path, "w") as vars_f:
                    json.dump({"config_cli": final_config_payload}, vars_f)

                inventory_file = f"/tmp/inventory_{final_target_name.replace(' ', '_')}.ini"
                
                safe_user = device.username.replace("\\", "\\\\") if device.username else "root"
                safe_pass = device.password.replace("\\", "\\\\") if device.password else ""
                safe_host = device.host.replace("\\", "\\\\")


                safe_host = device.host.replace("\\", "\\\\")
                # ==============================================================
                # MAPPING FQCN
                # ==============================================================
                vendor_db = device.vendor.lower()
                
                become_status = "no"
                become_method = ""
                
                if vendor_db == 'ce' or vendor_db == 'vrp':
                    ansible_os = 'community.network.ce'
                    terminal_type = "vt100"
                    become_status = "no"  
                    become_method = "ansible_become_method=enable ansible_become_password='{safe_pass}'"
                elif vendor_db == 'routeros' or vendor_db == 'mikrotik':
                    ansible_os = 'community.routeros.routeros'
                    terminal_type = "dumb"
                    if "+ctw" not in safe_user:
                        safe_user = f"{safe_user}+ctw"
                else:
                    ansible_os = vendor_db
                    terminal_type = "dumb"

                with open(inventory_file, "w") as f:
                    f.write("[routers]\n")
                    f.write(f"{final_target_name.replace(' ', '_')} "
                            f"ansible_host={safe_host} "
                            f"ansible_user={safe_user} "
                            f"ansible_port={device.port} "
                            f"ansible_password='{safe_pass}' "
                            f"ansible_become={become_status} "
                            f"{become_method} "
                            f"ansible_network_os={ansible_os} "
                            f"ansible_connection=network_cli "
                            f"ansible_terminal_type={terminal_type} "
                            f"ansible_command_timeout=60 "
                            f"ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KexAlgorithms=+diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc,3des-cbc -o PubkeyAuthentication=no -o GSSAPIAuthentication=no -o AddressFamily=inet'\n")
                # Menjalankan Subprocess Playbook Ansible

                print("\n Menjalankan Playbook Ansible...")
                t0_ansible_conf = time.time()
                
                playbook_path = "/home/kyo/ta/ansible/apply_config.yml"   
                playbook_cmd = [
                    "ansible-playbook",
                    playbook_path,
                    "-i", inventory_file,
                    "-e", f"@{vars_file_path}"
                ]
       
                result = subprocess.run(
                    playbook_cmd,
                    env={
                        **os.environ, 
                        "ANSIBLE_HOST_KEY_CHECKING": "False",
                        "ANSIBLE_DEPRECATION_WARNINGS": "False",
                        "ANSIBLE_CONFIG": "/home/kyo/ta/ansible/ansible.cfg",
                        "ANSIBLE_PERSISTENT_COMMAND_TIMEOUT": "30",
                        "ANSIBLE_PERSISTENT_CONNECT_TIMEOUT": "30",
                        "ANSIBLE_GATHERING": "explicit",
                        "ANSIBLE_INJECT_FACT_VARS": "False"
                    },
                    
                    capture_output=True,
                    text=True
                )

                waktu_ansible_conf = time.time() - t0_ansible_conf
                print(f"⚙️ [LOG PENGUJIAN CONFIG] Waktu Eksekusi Ansible: {waktu_ansible_conf:.3f} detik\n")
                
                print(f"\n{'='*20} ANSIBLE OUTPUT: {final_target_name} {'='*20}")
                print(">>> STDOUT (Output Normal):")
                print(result.stdout if result.stdout else "[KOSONG]")
                
                print("\n>>> STDERR (Error/Warning):")
                print(result.stderr if result.stderr else "[KOSONG]")
                print(f"{'='*60}\n")

                # Cleaning File Temporary
                if os.path.exists(inventory_file):
                    os.remove(inventory_file)
                if os.path.exists(vars_file_path):
                    os.remove(vars_file_path)              
                # ==========================================================
                # Menerjemahkan Raw Log jadi Feedback User
                # ==========================================================

                stdout_text_lower = result.stdout.lower() if result.stdout else ""
                stderr_text_lower = result.stderr.lower() if result.stderr else ""
                combined_log = stdout_text_lower + stderr_text_lower

                cmd_failed = ""
                sys_msg = ""
                detail_block = ""
                raw_stdout = result.stdout if result.stdout else ""
                
                match_huawei = re.search(r"(?i)command:\s*([^,]+),\s*b'([^']+)'", raw_stdout)
                match_mikrotik_item = re.search(r'failed:\s*\[.*?\]\s*\(item=(.*?)\)\s*=>\s*(\{.*?\})', raw_stdout, re.DOTALL)
                
                if match_huawei:
                    cmd_failed = match_huawei.group(1).strip()
                    sys_msg = match_huawei.group(2).replace('\\r\\n', ' ').replace('\\n', ' ').strip()
                elif match_mikrotik_item:
                    cmd_failed = match_mikrotik_item.group(1).strip()
                    raw_json = match_mikrotik_item.group(2)
                    stdout_match = re.search(r'"stdout":\s*"([^"]+)"', raw_json)
                    if stdout_match:
                        sys_msg = stdout_match.group(1).replace('\\n', ' ').replace('\\r', '').strip()
                        if sys_msg.startswith("/ "): sys_msg = sys_msg[2:]
                    else:
                        sys_msg = "Sintaks ditolak oleh perangkat."
                else:
                    match_generic = re.search(r'(?i)error:\s*(.*)', raw_stdout)
                    if match_generic:
                        sys_msg = match_generic.group(1).strip()

                if cmd_failed or sys_msg:
                    detail_block = "\n\n**Detail Kegagalan:**\n"
                    if cmd_failed:
                        detail_block += f"- **Perintah:** `{cmd_failed}`\n"
                    if sys_msg:
                        detail_block += f"- **Alasan:** {sys_msg}"

                # ----------------------------------------------------------
                # 2. Penentuan Judul Error Utama
                # ----------------------------------------------------------
                feedback_msg = f"Konfigurasi berhasil diterapkan ke perangkat {final_target_name}!"
                status_flag = "success"
                error_title = ""

                syntax_errors = [
                    "unrecognized command", "bad command", "syntax error", "input does not match",
                    "expected end of command", "expected command name", "failure:", "invalid",
                    "duplicate item name", "unknown error", "no such item", "incomplete command"
                ]

                if "unreachable=" in stdout_text_lower and not "unreachable=0" in stdout_text_lower:
                    error_title = "Tidak dapat menghubungi perangkat (Timeout/Unreachable)."
                elif "timed out" in combined_log or "timeout" in combined_log:
                    error_title = "Koneksi SSH ke perangkat terputus (Timeout)."
                elif any(x in combined_log for x in ["authentication failed", "permission denied", "auth failed"]):
                    error_title = "Autentikasi ditolak. Cek Username dan Password di Database."
                elif "conflicts with another address" in combined_log or "already have such address" in combined_log:
                    conflict_int = ""
                    find_int = re.search(r'\[(.*?)\]', combined_log)
                    if find_int:
                        conflict_int = f" di antarmuka **{find_int.group(1)}**"
                    error_title = f"IP Address sudah terpasang atau bentrok (Conflict){conflict_int}."
                elif any(x in combined_log for x in syntax_errors):
                    error_title = "Terdapat sintaks perintah yang tidak valid atau antarmuka tidak ditemukan."
                elif "ignored=" in stdout_text_lower and not "ignored=0" in stdout_text_lower:
                    error_title = "Sebagian perintah tidak dikenali dan diabaikan oleh perangkat."
                elif "failed=" in stdout_text_lower and not "failed=0" in stdout_text_lower:
                    error_title = "Terjadi kegagalan eksekusi pada perangkat."
                elif "error:" in combined_log:
                    error_title = "Terjadi error internal pada perangkat saat eksekusi."


                if error_title:
                    status_flag = "error"
                    feedback_msg = f"**Gagal diterapkan pada {final_target_name}:** {error_title}{detail_block}"

                final_results.append({
                    "target": final_target_name,
                    "status": status_flag,
                    "feedback": feedback_msg,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })

            except Exception as e:
                print(f"Error executing task for {final_target_name}: {e}")
                final_results.append({
                    "target": final_target_name, 
                    "status": "exception", 
                    "feedback": f"Error Sistem: Gagal mengeksekusi subprocess. ({str(e)})", 
                    "error": str(e)
                })

        return Response({
            "message": f"Selesai memproses {len(tasks)} tugas.",
            "results": final_results
        }, status=200)

    except Exception as e:
        print("CRITICAL ERROR:", e)
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)


# Membaca Informasi Perangkat
def execute_read_device(target_name_input, command):
    try:
        # 1. LOGIKA PENCARIAN TARGET PERANGKAT
        final_target_name = None
        try:
            alias_entry = DeviceAlias.objects.get(alias_name__iexact=target_name_input)
            final_target_name = alias_entry.device.name
        except DeviceAlias.DoesNotExist:
            try:
                device_obj = NetworkDevice.objects.get(name__iexact=target_name_input)
                final_target_name = device_obj.name
            except NetworkDevice.DoesNotExist:
                clean_target = target_name_input.lower().replace(" ", "").replace("_", "").replace("-", "")
                all_devices = NetworkDevice.objects.all()
                for d in all_devices:
                    if d.name.lower().replace(" ", "").replace("_", "").replace("-", "") == clean_target:
                        final_target_name = d.name
                        break
        
        if not final_target_name:
            return f" Gagal: Perangkat '{target_name_input}' tidak ditemukan di database."

        device = NetworkDevice.objects.get(name=final_target_name)
        vars_file_path = f"/tmp/vars_read_{final_target_name.replace(' ', '_')}.json"
        
        with open(vars_file_path, "w") as vars_f:
            json.dump({"target_command": command}, vars_f)

        inventory_file = f"/tmp/inventory_read_{final_target_name.replace(' ', '_')}.ini"
        safe_user = device.username.replace("\\", "\\\\") if device.username else "root"
        safe_pass = device.password.replace("\\", "\\\\") if device.password else ""
        safe_host = device.host.replace("\\", "\\\\")
        
        # ==============================================================
        # 2. MAPPING FQCN (Nama Lengkap OS untuk Ansible)
        # ==============================================================
        vendor_db = device.vendor.lower()

        if vendor_db == 'routeros' or vendor_db == 'mikrotik':
            if "+ctw" not in safe_user:
                safe_user = f"{safe_user}+ctw"
        
        if vendor_db == 'ce' or vendor_db == 'vrp':
            ansible_os = 'community.network.ce'
            terminal_type = "vt100"
            
        elif vendor_db == 'routeros' or vendor_db == 'mikrotik':
            ansible_os = 'community.routeros.routeros'
            terminal_type = "dumb"
            
        else:
            ansible_os = vendor_db
            terminal_type = "dumb"

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
                    f"ansible_terminal_type={terminal_type} "   
                    f"ansible_command_timeout=60 "
                    f"ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KexAlgorithms=+diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc,3des-cbc -o PubkeyAuthentication=no -o GSSAPIAuthentication=no -o AddressFamily=inet'\n")

        # ==============================================================
        # 3. JALANKAN ANSIBLE READ
        # ==============================================================
        playbook_path = "/home/kyo/ta/ansible/read_device.yml"
        playbook_cmd = [
            "ansible-playbook", playbook_path,
            "-i", inventory_file,
            "-e", f"@{vars_file_path}"
        ]

        result = subprocess.run(
            playbook_cmd,
            env={
                **os.environ, 
                "ANSIBLE_HOST_KEY_CHECKING": "False",
                "ANSIBLE_DEPRECATION_WARNINGS": "False",
                "ANSIBLE_CONFIG": "/home/kyo/ta/ansible/ansible.cfg",
                "ANSIBLE_PERSISTENT_COMMAND_TIMEOUT": "30",
                "ANSIBLE_PERSISTENT_CONNECT_TIMEOUT": "30",
                "ANSIBLE_GATHERING": "explicit",
                "ANSIBLE_INJECT_FACT_VARS": "False"
            },
            
            capture_output=True,
            text=True
        )

        # Hapus file sementara
        if os.path.exists(inventory_file): os.remove(inventory_file)
        if os.path.exists(vars_file_path): os.remove(vars_file_path)

        # ==============================================================
        # 4. PARSING HASIL DENGAN REGEX
        # ==============================================================
        if result.returncode == 0 or result.returncode == 2:
            try:
                match = re.search(r'"msg":\s*"(.*?)"\s*}', result.stdout, re.DOTALL)
                
                if match:
                    raw_output = match.group(1)
                    clean_output = raw_output.encode('utf-8').decode('unicode_escape')
                    clean_output = clean_output.strip()
                    return clean_output
                else:
                    return f" Berhasil dieksekusi, tapi gagal menemukan blok 'msg' di output.\n\nRaw Output:\n{result.stdout}"
            except Exception as e:
                return f" Gagal mengekstrak teks: {str(e)}\n\nRaw:\n{result.stdout}"
        
        else:
            return f" Gagal mengambil data. Detail error:\n{result.stderr or result.stdout}"

    except Exception as e:
        return f" Kesalahan sistem: {str(e)}"


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
