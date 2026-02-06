import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import copy

# -----------------------------
# Data Model
# -----------------------------
class Process:
    def __init__(self, pid, arrival, burst, priority):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.priority = priority
        self.remaining = burst
        self.start = None
        self.finish = None
        self.waiting_time = 0
        self.turnaround_time = 0
        self.executed_slices = 0
        self.last_executed = -1

    def attention_score(self, current_time, history_length):
        # How long it has been waiting since last execution
        if self.last_executed == -1:
            recency = current_time - self.arrival
        else:
            recency = current_time - self.last_executed

        # Penalize CPU hogs
        fairness = 1 / (1 + self.executed_slices)

        # Prefer shorter remaining jobs
        burst_factor = 1 / self.remaining

        # Priority still matters, but less
        priority_factor = 1 / (1 + self.priority)

        # Attention-style weighted context
        return (
            0.4 * recency +
            0.3 * burst_factor +
            0.2 * fairness +
            0.1 * priority_factor
        )
    
    def get_attention_components(self, current_time):
        """Get individual components of attention score for visualization"""
        if self.last_executed == -1:
            recency = current_time - self.arrival
        else:
            recency = current_time - self.last_executed
        
        fairness = 1 / (1 + self.executed_slices)
        burst_factor = 1 / self.remaining
        priority_factor = 1 / (1 + self.priority)
        
        return {
            'recency': recency,
            'recency_weighted': 0.4 * recency,
            'burst': burst_factor,
            'burst_weighted': 0.3 * burst_factor,
            'fairness': fairness,
            'fairness_weighted': 0.2 * fairness,
            'priority': priority_factor,
            'priority_weighted': 0.1 * priority_factor
        }


processes = []
animation_running = False
animation_id = None
selection_history = []
resume_callback = None

# -----------------------------
# UI State Management
# -----------------------------
paused = False

def update_button_states():
    global paused
    if animation_running:
        add_button.config(state="disabled")
        run_button.config(state="disabled")
        if paused:
            stop_button.config(text="▶ Resume", bg="#27AE60", activebackground="#2ECC71", state="normal")
        else:
            stop_button.config(text="⏸ Pause", bg="#E67E22", activebackground="#F39C12", state="normal")
    else:
        add_button.config(state="normal")
        run_button.config(state="normal" if processes else "disabled")
        stop_button.config(text="⏸ Pause", state="disabled")

# -----------------------------
# UI Functions
# -----------------------------
def open_add_process():
    global animation_running, paused

    if animation_running:
        messagebox.showwarning("Warning", "Cannot add processes while animation is running!")
        return
    
    processes.clear()
    selection_history.clear()
    paused = False
    gantt_canvas.delete("all")
    attention_canvas.delete("all")
    comparison_text.config(state="normal")
    comparison_text.delete("1.0", tk.END)
    comparison_text.config(state="disabled")
    time_label.config(text="Time: 0")
    running_label.config(text="Running: —")
    avg_waiting_label.config(text="Avg Waiting Time: —")
    avg_turnaround_label.config(text="Avg Turnaround Time: —")

    modal = tk.Toplevel(root)
    modal.title("Add Processes")
    modal.geometry("700x600")
    modal.transient(root)
    modal.grab_set()
    modal.configure(bg="#F8F9FA")

    title_frame = tk.Frame(modal, bg="#2C5F2D", height=60)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)
    
    title_label = tk.Label(
        title_frame, text="Add Processes", bg="#2C5F2D",
        font=("Segoe UI", 16, "bold"), fg="white"
    )
    title_label.pack(expand=True)

    main_frame = tk.Frame(modal, bg="#F8F9FA")
    main_frame.pack(fill="both", expand=True, padx=30, pady=20)

    headers_frame = tk.Frame(main_frame, bg="#F8F9FA")
    headers_frame.pack(fill="x", pady=(0, 10))

    headers = ["PID", "Arrival Time", "Burst Time", "Priority"]
    for idx, header in enumerate(headers):
        lbl = tk.Label(
            headers_frame, text=header, bg="#2C5F2D", fg="white",
            font=("Segoe UI", 11, "bold"), width=15, height=2,
            relief="flat"
        )
        lbl.grid(row=0, column=idx, padx=3, pady=0, sticky="ew")
        headers_frame.grid_columnconfigure(idx, weight=1, uniform="col")

    canvas_frame = tk.Frame(main_frame, bg="white", relief="solid", bd=2)
    canvas_frame.pack(fill="both", expand=True, pady=(0, 15))

    canvas = tk.Canvas(canvas_frame, bg="white", height=300, highlightthickness=0)
    scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    entries_container = tk.Frame(canvas, bg="white")

    canvas.create_window((0, 0), window=entries_container, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas.find_all()[0], width=canvas.winfo_width())

    entries_container.bind("<Configure>", on_frame_configure)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    entries_list = []

    def create_entry_row():
        row_frame = tk.Frame(entries_container, bg="white")
        row_frame.pack(fill="x", pady=3, padx=5)

        row_entries = []
        for _ in range(4):
            entry = tk.Entry(
                row_frame, font=("Segoe UI", 11),
                relief="solid", bd=1, justify="center",
                bg="white", fg="#2C3E50"
            )
            entry.pack(side="left", padx=3, expand=True, fill="x")
            row_entries.append(entry)

        entries_list.append(row_entries)

        row_entries[-1].bind(
            "<KeyRelease>",
            lambda e: create_entry_row()
            if entries_list[-1] == row_entries and all(x.get().strip() for x in row_entries)
            else None
        )

    for _ in range(4):
        create_entry_row()

    def save_processes():
        seen_pids = {p.pid for p in processes}
        new_pids = set()
        batch = []

        for row in entries_list:
            pid = row[0].get().strip()
            arrival = row[1].get().strip()
            burst = row[2].get().strip()
            priority = row[3].get().strip()

            filled = [pid, arrival, burst, priority]

            # Row is completely empty → ignore
            if all(not field for field in filled):
                continue

            # Row is partially filled → ERROR
            if not all(filled):
                messagebox.showerror(
                    "Missing Data",
                    "Each process must have PID, Arrival Time, Burst Time, and Priority filled.\n\n"
                    "Please complete all fields or clear the row."
                )
                return


            if pid in new_pids:
                messagebox.showerror("Error", f"Duplicate PID '{pid}' in current entries!")
                return

            if pid in seen_pids:
                messagebox.showerror("Error", f"PID '{pid}' already exists!")
                return

            try:
                arr = int(arrival)
                bur = int(burst)
                pri = int(priority)
                if arr < 0 or bur <= 0 or pri < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", f"Invalid values for PID '{pid}'!")
                return

            new_pids.add(pid)
            batch.append(Process(pid, arr, bur, pri))

        if not batch:
            messagebox.showwarning("Warning", "No valid processes to add!")
            return

        processes.extend(batch)
        update_button_states()
        messagebox.showinfo("Success", f"{len(batch)} process(es) added!")
        modal.destroy()

    def delete_all_processes():
        if processes:
            if messagebox.askyesno("Confirm", f"Delete all {len(processes)} processes?"):
                processes.clear()
                messagebox.showinfo("Success", "All processes deleted!")
                update_button_states()
                modal.destroy()
        else:
            messagebox.showinfo("Info", "No processes to delete!")
            modal.destroy()

    button_frame = tk.Frame(modal, bg="#F8F9FA")
    button_frame.pack(pady=(0, 20))

    save_btn = tk.Button(
        button_frame, text="Save Processes", font=("Segoe UI", 12, "bold"),
        bg="#2C5F2D", fg="white", width=18, height=2,
        relief="flat", cursor="hand2",
        activebackground="#3D7C3E", activeforeground="white",
        command=save_processes
    )
    save_btn.pack(side="left", padx=8)
    
    delete_btn = tk.Button(
        button_frame, text="Delete All", font=("Segoe UI", 12, "bold"),
        bg="#C62828", fg="white", width=18, height=2,
        relief="flat", cursor="hand2",
        activebackground="#D32F2F", activeforeground="white",
        command=delete_all_processes
    )
    delete_btn.pack(side="left", padx=8)


def draw_attention_visualization(ready_queue, current_time, selected_process, algorithm):
    """Draw comprehensive attention score visualization"""
    attention_canvas.delete("all")
    
    if not ready_queue:
        attention_canvas.create_text(
            400, 100,
            text="No processes in ready queue",
            font=("Segoe UI", 13), fill="#95A5A6"
        )
        return
    
    canvas_width = 800
    canvas_height = 220
    
    # Calculate scores for all processes
    process_scores = []
    for p in ready_queue:
        score = p.attention_score(current_time, 0)
        components = p.get_attention_components(current_time)
        process_scores.append((p, score, components))
    
    # Sort by attention score (descending)
    process_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Find traditional algorithm choice for comparison
    traditional_choice = None
    if algorithm == "FCFS":
        traditional_choice = min(ready_queue, key=lambda p: p.arrival)
    elif algorithm == "SJF":
        traditional_choice = min(ready_queue, key=lambda p: p.remaining)
    elif algorithm == "Priority":
        traditional_choice = min(ready_queue, key=lambda p: p.priority)
    elif algorithm == "Round Robin":
        traditional_choice = ready_queue[0]
    
    # Calculate centering offset for left section
    num_processes = len(process_scores)
    total_left_height = num_processes * 33  # bar_height + spacing
    left_start_y = max(40, (canvas_height - total_left_height) / 2 + 20)
    
    # === LEFT SIDE: Attention Scores Bar Chart (CENTERED) ===
    left_margin = 50
    bar_height = 25
    max_score = max(score for _, score, _ in process_scores) if process_scores else 1
    bar_max_width = 220
    
    # Title
    attention_canvas.create_text(
        left_margin + 110, 15,
        text="Process Attention Scores",
        font=("Segoe UI", 11, "bold"),
        fill="#8E44AD"
    )
    
    for idx, (proc, score, components) in enumerate(process_scores):
        y = left_start_y + idx * 33
        bar_width = (score / max_score) * bar_max_width if max_score > 0 else 0
        
        # Determine color
        if proc == selected_process:
            color = "#E74C3C"  # Red for SELECTED
            text_color = "white"
            prefix = "✓ "
        elif proc == traditional_choice and proc != selected_process:
            color = "#F39C12"  # Orange for what traditional would pick
            text_color = "white"
            prefix = "⚠ "
        else:
            color = "#95A5A6"  # Gray for others
            text_color = "white"
            prefix = ""
        
        # Draw bar
        attention_canvas.create_rectangle(
            left_margin, y, left_margin + bar_width, y + bar_height,
            fill=color, outline="#2C3E50", width=2
        )
        
        # Process label inside bar
        attention_canvas.create_text(
            left_margin + 10, y + bar_height/2,
            text=f"{prefix}P{proc.pid}",
            font=("Segoe UI", 10, "bold"),
            fill=text_color,
            anchor="w"
        )
        
        # Score value at end of bar
        attention_canvas.create_text(
            left_margin + bar_width + 40, y + bar_height/2,
            text=f"{score:.3f}",
            font=("Segoe UI", 9, "bold"),
            fill=color
        )
    
    # === RIGHT SIDE: Component Breakdown for Selected Process ===
    if selected_process:
        selected_components = selected_process.get_attention_components(current_time)
        
        right_start = 380
        component_start_y = 40
        component_bar_height = 20
        component_max_width = 180
        
        # Title
        attention_canvas.create_text(
            right_start + 110, 15,
            text=f"P{selected_process.pid} Component Breakdown",
            font=("Segoe UI", 11, "bold"),
            fill="#E74C3C"
        )
        
        components_display = [
            ("Recency", selected_components['recency_weighted'], "#3498DB", 
             f"Wait: {selected_components['recency']:.1f}"),
            ("Burst", selected_components['burst_weighted'], "#2ECC71",
             f"Rem: {selected_process.remaining}"),
            ("Fairness", selected_components['fairness_weighted'], "#F39C12",
             f"Exec: {selected_process.executed_slices}"),
            ("Priority", selected_components['priority_weighted'], "#9B59B6",
             f"Pri: {selected_process.priority}")
        ]
        
        max_component = max(c[1] for c in components_display)
        
        for idx, (name, value, color, detail) in enumerate(components_display):
            y = component_start_y + idx * 35
            bar_width = (value / max_component) * component_max_width if max_component > 0 else 0
            
            # Label
            attention_canvas.create_text(
                right_start, y + component_bar_height/2,
                text=f"{name}:",
                font=("Segoe UI", 9, "bold"),
                fill="#2C3E50",
                anchor="w"
            )
            
            # Bar
            attention_canvas.create_rectangle(
                right_start + 70, y, right_start + 70 + bar_width, y + component_bar_height,
                fill=color, outline="#2C3E50", width=1
            )
            
            # Value
            attention_canvas.create_text(
                right_start + 70 + bar_width + 30, y + component_bar_height/2,
                text=f"{value:.3f}",
                font=("Segoe UI", 8, "bold"),
                fill=color
            )
            
            # Detail
            attention_canvas.create_text(
                right_start + 70 + bar_width + 75, y + component_bar_height/2,
                text=detail,
                font=("Segoe UI", 8),
                fill="#7F8C8D",
                anchor="w"
            )
    
    # === BOTTOM: Legend ===
    legend_y = 185
    attention_canvas.create_text(
        80, legend_y,
        text="✓ Attention Choice",
        font=("Segoe UI", 9, "bold"),
        fill="#E74C3C",
        anchor="w"
    )
    
    if traditional_choice and traditional_choice != selected_process:
        attention_canvas.create_text(
            240, legend_y,
            text=f"⚠ Traditional {algorithm} Choice",
            font=("Segoe UI", 9, "bold"),
            fill="#F39C12",
            anchor="w"
        )


def draw_gantt_chart(gantt_history, current_time):
    """Draw Gantt chart up to current time with all start and end times"""
    gantt_canvas.delete("all")
    
    canvas_width = gantt_canvas.winfo_width() if gantt_canvas.winfo_width() > 1 else 950
    canvas_height = 150
    
    if not gantt_history:
        gantt_canvas.create_text(
            canvas_width / 2, canvas_height / 2, 
            text="Gantt Chart - Waiting for processes...", 
            font=("Segoe UI", 13), fill="#95A5A6"
        )
        return

    max_time = max(current_time, max([end for _, _, end in gantt_history]) if gantt_history else 1)
    margin = 60
    scale = (canvas_width - 2 * margin) / max(max_time, 1)

    colors = ["#52B788", "#74C69D", "#95D5B2", "#40916C", "#2D6A4F", "#1B4332", "#52796F", "#6A994E"]
    
    # Center the gantt chart vertically
    height = 50
    y_pos = (canvas_height - height) / 2 - 10  # Centered with room for time labels

    pid_color_map = {}
    color_idx = 0
    
    for idx, (pid, start, end) in enumerate(gantt_history):
        if pid not in pid_color_map:
            pid_color_map[pid] = colors[color_idx % len(colors)]
            color_idx += 1
        
        x1 = margin + start * scale
        x2 = margin + end * scale
        color = pid_color_map[pid]
        
        # Draw shadow
        gantt_canvas.create_rectangle(
            x1 + 2, y_pos + 2, x2 + 2, y_pos + height + 2, 
            fill="#BDC3C7", outline=""
        )
        # Draw main rectangle
        gantt_canvas.create_rectangle(
            x1, y_pos, x2, y_pos + height, 
            fill=color, outline="#2C3E50", width=2
        )
        
        # Draw process label
        gantt_canvas.create_text(
            (x1 + x2) / 2, y_pos + height / 2, 
            text=f"P{pid}", font=("Segoe UI", 11, "bold"), fill="white"
        )
        
        # Always draw start time line and label for each segment
        gantt_canvas.create_line(x1, y_pos + height, x1, y_pos + height + 15, width=2, fill="#34495E")
        gantt_canvas.create_text(x1, y_pos + height + 28, text=str(start), font=("Segoe UI", 10, "bold"), fill="#2C3E50")
        
        # Always draw end time line and label for each segment
        gantt_canvas.create_line(x2, y_pos + height, x2, y_pos + height + 15, width=2, fill="#34495E")
        gantt_canvas.create_text(x2, y_pos + height + 28, text=str(end), font=("Segoe UI", 10, "bold"), fill="#2C3E50")


def update_comparison_text(algorithm, selected_process, ready_queue, current_time):
    """Update the comparison text showing why attention made a different choice"""
    comparison_text.config(state="normal")
    comparison_text.delete("1.0", tk.END)
    
    if not selected_process or not ready_queue:
        comparison_text.config(state="disabled")
        return
    
    # Determine what traditional algorithm would pick
    traditional_choice = None
    traditional_reason = ""
    
    if algorithm == "FCFS":
        traditional_choice = min(ready_queue, key=lambda p: p.arrival)
        traditional_reason = f"earliest arrival time ({traditional_choice.arrival})"
    elif algorithm == "SJF":
        traditional_choice = min(ready_queue, key=lambda p: p.remaining)
        traditional_reason = f"shortest remaining time ({traditional_choice.remaining})"
    elif algorithm == "Priority":
        traditional_choice = min(ready_queue, key=lambda p: p.priority)
        traditional_reason = f"highest priority ({traditional_choice.priority})"
    elif algorithm == "Round Robin":
        traditional_choice = ready_queue[0]
        traditional_reason = "first in queue"
    
    comparison_text.tag_config("header", foreground="#8E44AD", font=("Segoe UI", 11, "bold"))
    comparison_text.tag_config("attention", foreground="#E74C3C", font=("Segoe UI", 10, "bold"))
    comparison_text.tag_config("traditional", foreground="#F39C12", font=("Segoe UI", 10, "bold"))
    comparison_text.tag_config("same", foreground="#27AE60", font=("Segoe UI", 10, "bold"))
    comparison_text.tag_config("detail", foreground="#34495E", font=("Segoe UI", 9))
    
    if traditional_choice == selected_process:
        comparison_text.insert("end", "⚖️ AGREEMENT\n", "header")
        comparison_text.insert("end", f"\nBoth Attention and {algorithm} selected ", "detail")
        comparison_text.insert("end", f"P{selected_process.pid}\n", "same")
        comparison_text.insert("end", f"\n• {algorithm}: {traditional_reason}\n", "detail")
        comparison_text.insert("end", f"• Attention: Score {selected_process.attention_score(current_time, 0):.3f}\n", "detail")
    else:
        comparison_text.insert("end", "⚡ ATTENTION OVERRIDE!\n", "header")
        comparison_text.insert("end", f"\nAttention chose ", "detail")
        comparison_text.insert("end", f"P{selected_process.pid}", "attention")
        comparison_text.insert("end", f" over traditional {algorithm} choice ", "detail")
        comparison_text.insert("end", f"P{traditional_choice.pid}\n", "traditional")
        
        comparison_text.insert("end", f"\n{algorithm} would pick P{traditional_choice.pid}:\n", "traditional")
        comparison_text.insert("end", f"  └─ Reason: {traditional_reason}\n", "detail")
        
        sel_comps = selected_process.get_attention_components(current_time)
        comparison_text.insert("end", f"\nAttention picked P{selected_process.pid}:\n", "attention")
        comparison_text.insert("end", f"  └─ Total Score: {selected_process.attention_score(current_time, 0):.3f}\n", "detail")
        comparison_text.insert("end", f"  └─ Waited {sel_comps['recency']:.1f} units\n", "detail")
        comparison_text.insert("end", f"  └─ Only {selected_process.remaining} burst left\n", "detail")
        comparison_text.insert("end", f"  └─ Executed {selected_process.executed_slices} times\n", "detail")
    
    comparison_text.config(state="disabled")


def update_queues(ready_queue, waiting_queue, completed, current_time):
    """Update the ready and waiting queue displays"""
    ready_box.config(state="normal")
    waiting_box.config(state="normal")
    
    ready_box.delete("1.0", tk.END)
    waiting_box.delete("1.0", tk.END)
    
    if ready_queue:
        sorted_ready = sorted(ready_queue, key=lambda p: p.attention_score(current_time, 0), reverse=True)
        
        ready_text = "Ready Queue (by attention):\n\n"
        for idx, p in enumerate(sorted_ready):
            attn = p.attention_score(current_time, 0)
            indicator = "→ " if idx == 0 else "   "
            ready_text += f"{indicator}P{p.pid}: {attn:.3f}\n"
        ready_box.insert("1.0", ready_text)
    else:
        ready_box.insert("1.0", "Ready Queue:\n\n  Empty")
    
    if waiting_queue:
        waiting_text = "Waiting Queue:\n\n"
        for p in waiting_queue:
            waiting_text += f"  P{p.pid}  —  Arrives: {p.arrival}\n"
        waiting_box.insert("1.0", waiting_text)
    elif completed:
        waiting_box.insert("1.0", f"✓ All Completed!\n\nTotal: {len(completed)}")
    else:
        waiting_box.insert("1.0", "Waiting Queue:\n\n  Empty")
    
    ready_box.config(state="disabled")
    waiting_box.config(state="disabled")


def toggle_pause_resume():
    """Toggle between pause and resume"""
    global paused, animation_id, resume_callback
    
    if not animation_running:
        return
    
    if paused:
        # Resume
        paused = False
        update_button_states()
        # Resume the animation by calling the stored callback
        if resume_callback:
            resume_callback()
    else:
        # Pause
        paused = True
        if animation_id:
            root.after_cancel(animation_id)
            animation_id = None
        update_button_states()


def animate_scheduler(algorithm, procs, quantum=2):
    global animation_running, animation_id, selection_history, paused, resume_callback
    
    time = [0]
    gantt = []
    ready = []
    waiting = list(procs)
    completed = []
    current_process = [None]
    remaining_burst = [0]
    
    waiting.sort(key=lambda p: p.arrival)
    
    def step():
        global animation_running, animation_id, paused
        
        if not animation_running:
            return
        
        # Check if paused
        if paused:
            # Don't schedule next step, wait for resume
            return
        
        current_time = time[0]
        
        arrived = [p for p in waiting if p.arrival <= current_time]
        for p in arrived:
            waiting.remove(p)
            ready.append(p)
        
        if current_process[0] is None and ready:
            if algorithm == "FCFS":
                candidate_list = ready
            elif algorithm == "SJF":
                candidate_list = sorted(ready, key=lambda p: p.remaining)
            elif algorithm == "Priority":
                candidate_list = sorted(ready, key=lambda p: p.priority)
            elif algorithm == "Round Robin":
                candidate_list = ready
            else:
                candidate_list = ready

            selected = max(
                candidate_list,
                key=lambda p: p.attention_score(current_time, len(gantt))
            )
            
            selection_record = {
                'time': current_time,
                'selected': selected.pid,
                'attention_score': selected.attention_score(current_time, len(gantt)),
                'candidates': {p.pid: p.attention_score(current_time, len(gantt)) for p in candidate_list}
            }
            selection_history.append(selection_record)
            
            current_process[0] = selected
            ready.remove(current_process[0])

            remaining_burst[0] = min(
                quantum if algorithm == "Round Robin" else current_process[0].remaining,
                current_process[0].remaining
            )

            if current_process[0].start is None:
                current_process[0].start = current_time
            
            # Update comparison
            ready_for_comparison = [p for p in ready] + [current_process[0]]
            update_comparison_text(algorithm, current_process[0], ready_for_comparison, current_time)
        
        draw_attention_visualization(ready + ([current_process[0]] if current_process[0] else []), 
                                    current_time, current_process[0], algorithm)
        
        if current_process[0]:
            p = current_process[0]
            p.executed_slices += 1
            p.last_executed = current_time
            
            if not gantt or gantt[-1][0] != p.pid:
                gantt.append([p.pid, current_time, current_time + 1])
            else:
                gantt[-1][2] = current_time + 1
            
            p.remaining -= 1
            remaining_burst[0] -= 1
            
            running_label.config(text=f"Running: P{p.pid}  ({p.burst - p.remaining}/{p.burst})")
            
            if p.remaining == 0:
                p.finish = current_time + 1
                p.turnaround_time = p.finish - p.arrival
                p.waiting_time = p.turnaround_time - p.burst
                completed.append(p)
                current_process[0] = None
                remaining_burst[0] = 0
            elif algorithm == "Round Robin" and remaining_burst[0] == 0:
                arrived = [proc for proc in waiting if proc.arrival <= current_time + 1]
                for proc in arrived:
                    waiting.remove(proc)
                    ready.append(proc)
                
                ready.append(p)
                current_process[0] = None
                remaining_burst[0] = 0
        else:
            running_label.config(text="Running: —")
        
        time_label.config(text=f"Time: {current_time+1}")
        draw_gantt_chart([(g[0], g[1], g[2]) for g in gantt], current_time)
        update_queues(ready, waiting, completed, current_time)
        
        if not waiting and not ready and current_process[0] is None:
            animation_running = False
            paused = False
            update_button_states()
            
            if completed:
                avg_wt = sum(p.waiting_time for p in completed) / len(completed)
                avg_tat = sum(p.turnaround_time for p in completed) / len(completed)
                avg_waiting_label.config(text=f"Avg Waiting: {avg_wt:.2f}")
                avg_turnaround_label.config(text=f"Avg Turnaround: {avg_tat:.2f}")
            
            messagebox.showinfo("Complete", f"Done! Attention made {len(selection_history)} decisions")
            return
        
        time[0] += 1
        animation_id = root.after(600, step)
    
    # Store the step function so it can be called on resume
    resume_callback = step
    step()


def run_scheduler():
    global animation_running, animation_id, selection_history, paused
    
    if not processes:
        messagebox.showwarning("Warning", "Please add processes first!")
        return
    
    if animation_running:
        messagebox.showwarning("Warning", "Animation already running!")
        return
    
    paused = False
    selection_history.clear()
    gantt_canvas.delete("all")
    attention_canvas.delete("all")
    comparison_text.config(state="normal")
    comparison_text.delete("1.0", tk.END)
    comparison_text.config(state="disabled")
    ready_box.config(state="normal")
    waiting_box.config(state="normal")
    ready_box.delete("1.0", tk.END)
    waiting_box.delete("1.0", tk.END)
    ready_box.config(state="disabled")
    waiting_box.config(state="disabled")
    time_label.config(text="Time: 0")
    running_label.config(text="Running: —")
    avg_waiting_label.config(text="Avg Waiting: —")
    avg_turnaround_label.config(text="Avg Turnaround: —")
    
    procs = [copy.deepcopy(p) for p in processes]
    
    algorithm = algorithm_var.get()
    animation_running = True
    update_button_states()
    
    animate_scheduler(algorithm, procs, quantum=2)


# -----------------------------
# Main Window
# -----------------------------
root = tk.Tk()
root.title("Attention-Based CPU Scheduler")
root.geometry("1100x900")
root.configure(bg="#ECF0F1")
root.resizable(True, True)

# Header
header_frame = tk.Frame(root, bg="#8E44AD", height=60)
header_frame.pack(fill="x")
header_frame.pack_propagate(False)

header_label = tk.Label(
    header_frame, text="Attention-Based CPU Scheduler",
    bg="#8E44AD", fg="white",
    font=("Segoe UI", 20, "bold")
)
header_label.pack(expand=True)

# Controls
control_frame = tk.Frame(root, bg="#ECF0F1")
control_frame.pack(fill="x", padx=30, pady=12)

left_control = tk.Frame(control_frame, bg="#ECF0F1")
left_control.pack(side="left")

algo_label = tk.Label(
    left_control, text="Base Algorithm:",
    bg="#ECF0F1", fg="#2C3E50",
    font=("Segoe UI", 11, "bold")
)
algo_label.pack(side="left", padx=(0, 10))

algorithm_var = tk.StringVar(value="FCFS")
algorithm_menu = ttk.Combobox(
    left_control,
    textvariable=algorithm_var,
    values=["FCFS", "SJF", "Priority", "Round Robin"],
    state="readonly",
    width=16,
    font=("Segoe UI", 10)
)
algorithm_menu.pack(side="left")

right_control = tk.Frame(control_frame, bg="#ECF0F1")
right_control.pack(side="right")

add_button = tk.Button(
    right_control,
    text="➕ Add Processes",
    bg="#2C5F2D",
    fg="white",
    font=("Segoe UI", 11, "bold"),
    width=15,
    height=2,
    relief="flat",
    cursor="hand2",
    command=open_add_process
)
add_button.pack(side="left", padx=5)

run_button = tk.Button(
    right_control,
    text="▶ Run",
    bg="#27AE60",
    fg="white",
    font=("Segoe UI", 11, "bold"),
    width=12,
    height=2,
    relief="flat",
    cursor="hand2",
    command=run_scheduler,
    state="disabled"
)
run_button.pack(side="left", padx=5)

stop_button = tk.Button(
    right_control,
    text="⏸ Pause",
    bg="#E67E22",
    fg="white",
    font=("Segoe UI", 11, "bold"),
    width=10,
    height=2,
    relief="flat",
    cursor="hand2",
    command=toggle_pause_resume,
    state="disabled"
)
stop_button.pack(side="left", padx=5)

# Attention Visualization
attention_container = tk.Frame(root, bg="#ECF0F1")
attention_container.pack(fill="x", padx=30, pady=(0, 10))

attention_frame = tk.Frame(attention_container, bg="white")
attention_frame.pack(fill="x")

attention_header = tk.Frame(attention_frame, bg="#8E44AD", height=32)
attention_header.pack(fill="x")
attention_header.pack_propagate(False)

tk.Label(
    attention_header, text="⚡ Attention Mechanism Criteria",
    bg="#8E44AD", fg="white",
    font=("Segoe UI", 12, "bold")
).pack(expand=True)

attention_canvas = tk.Canvas(attention_frame, bg="#FAFAFA", height=200, highlightthickness=0)
attention_canvas.pack(fill="x")

# Comparison Panel
comparison_container = tk.Frame(root, bg="#ECF0F1")
comparison_container.pack(fill="x", padx=30, pady=(0, 10))

comparison_frame = tk.Frame(comparison_container, bg="white")
comparison_frame.pack(fill="x")

comparison_header = tk.Frame(comparison_frame, bg="#9B59B6", height=32)
comparison_header.pack(fill="x")
comparison_header.pack_propagate(False)

tk.Label(
    comparison_header, text="🔄 TRADITIONAL vs ATTENTION",
    bg="#9B59B6", fg="white",
    font=("Segoe UI", 11, "bold")
).pack(expand=True)

comparison_text = tk.Text(
    comparison_frame, height=6, relief="flat",
    borderwidth=0, font=("Segoe UI", 10),
    bg="#F8F9FA", fg="#2C3E50",
    padx=15, pady=10, state="disabled", wrap="word"
)
comparison_text.pack(fill="x")

# Gantt Chart
gantt_container = tk.Frame(root, bg="#ECF0F1")
gantt_container.pack(fill="both", expand=True, padx=30, pady=(0, 10))

gantt_frame = tk.Frame(gantt_container, bg="white")
gantt_frame.pack(fill="both", expand=True)

gantt_header = tk.Frame(gantt_frame, bg="#34495E", height=32)
gantt_header.pack(fill="x")
gantt_header.pack_propagate(False)

tk.Label(
    gantt_header, text="📊 Gantt Chart",
    bg="#34495E", fg="white",
    font=("Segoe UI", 11, "bold")
).pack(side="left", padx=15)

gantt_canvas = tk.Canvas(gantt_frame, bg="#FAFAFA", height=150, highlightthickness=0)
gantt_canvas.pack(fill="both", expand=True)

# Bottom Panels
bottom_container = tk.Frame(root, bg="#ECF0F1")
bottom_container.pack(fill="both", padx=30, pady=(0, 10))

ready_frame = tk.Frame(bottom_container, bg="white")
ready_frame.pack(side="left", expand=True, fill="both", padx=(0, 10))

ready_header = tk.Frame(ready_frame, bg="#3498DB", height=32)
ready_header.pack(fill="x")
ready_header.pack_propagate(False)

tk.Label(
    ready_header, text="🔵 Ready Queue",
    fg="white", font=("Segoe UI", 10, "bold"),
    bg="#3498DB"
).pack(side="left", padx=15)

ready_box = tk.Text(
    ready_frame, height=5, relief="flat",
    borderwidth=0, font=("Segoe UI", 10),
    bg="#F8F9FA", fg="#2C3E50",
    padx=12, pady=8, state="disabled"
)
ready_box.pack(fill="both", expand=True)

waiting_frame = tk.Frame(bottom_container, bg="white")
waiting_frame.pack(side="left", expand=True, fill="both", padx=(10, 0))

waiting_header = tk.Frame(waiting_frame, bg="#E67E22", height=32)
waiting_header.pack(fill="x")
waiting_header.pack_propagate(False)

tk.Label(
    waiting_header, text="⏳ Waiting",
    fg="white", font=("Segoe UI", 10, "bold"),
    bg="#E67E22"
).pack(side="left", padx=15)

waiting_box = tk.Text(
    waiting_frame, height=5, relief="flat",
    borderwidth=0, font=("Segoe UI", 10),
    bg="#F8F9FA", fg="#2C3E50",
    padx=12, pady=8, state="disabled"
)
waiting_box.pack(fill="both", expand=True)

# Metrics Footer
metrics_container = tk.Frame(root, bg="#34495E", height=55)
metrics_container.pack(fill="x", side="bottom")
metrics_container.pack_propagate(False)

metrics_frame = tk.Frame(metrics_container, bg="#34495E")
metrics_frame.pack(expand=True)

left_metrics = tk.Frame(metrics_frame, bg="#34495E")
left_metrics.pack(side="left", padx=30)

avg_waiting_label = tk.Label(
    left_metrics, text="Avg Waiting: —",
    fg="#ECF0F1", font=("Segoe UI", 10, "bold"),
    bg="#34495E"
)
avg_waiting_label.pack(anchor="w", pady=1)

avg_turnaround_label = tk.Label(
    left_metrics, text="Avg Turnaround: —",
    fg="#ECF0F1", font=("Segoe UI", 10, "bold"),
    bg="#34495E"
)
avg_turnaround_label.pack(anchor="w", pady=1)

right_metrics = tk.Frame(metrics_frame, bg="#34495E")
right_metrics.pack(side="right", padx=30)

time_label = tk.Label(
    right_metrics, text="Time: 0",
    fg="#3498DB", font=("Segoe UI", 11, "bold"),
    bg="#34495E"
)
time_label.pack(anchor="e", pady=1)

running_label = tk.Label(
    right_metrics, text="Running: —",
    fg="#E74C3C", font=("Segoe UI", 11, "bold"),
    bg="#34495E"
)
running_label.pack(anchor="e", pady=1)

update_button_states()
root.mainloop()