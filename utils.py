import os
import re
from docx import Document
from docx.oxml.ns import qn

DEFAULT_IMAGE_DIR = "static/question_images"

def extract_table_html(table):
    html = "<table border='1' cellspacing='0' cellpadding='5'>"
    for row in table.rows:
        html += "<tr>"
        for cell in row.cells:
            html += f"<td>{cell.text.strip()}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def save_image_from_run(run, output_dir, image_counter):
    blip_elements = run._element.findall('.//a:blip', namespaces={
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    })

    if not blip_elements:
        return None

    rId = blip_elements[0].get(qn('r:embed'))
    image_part = run.part.related_parts[rId]
    image_data = image_part.blob

    image_filename = f"question_image_{image_counter}.png"
    image_path = os.path.join(output_dir, image_filename)

    with open(image_path, 'wb') as f:
        f.write(image_data)

    return image_filename

def parse_docx_questions(file_stream, image_output_dir=DEFAULT_IMAGE_DIR):
    document = Document(file_stream)
    questions = []
    current_question = None
    extra_html_parts = []
    image_counter = 0
    skipped = 0
    questions_started = False

    os.makedirs(image_output_dir, exist_ok=True)

    for para in document.paragraphs:
        text = para.text.strip()

        # Save any images embedded in the paragraph
        for run in para.runs:
            image_name = save_image_from_run(run, image_output_dir, image_counter + 1)
            if image_name and current_question:
                image_counter += 1
                current_question["image"] = image_name

        if not text:
            continue

        # Wait until question 1 is found before parsing anything
        if not questions_started:
            if re.match(r"^1[\.\)]", text):
                questions_started = True
            else:
                continue

        # Detect a new question
        if re.match(r"^\d+[\.\)]", text):
            if current_question:
                current_question["extra_content"] = ''.join(extra_html_parts) if extra_html_parts else None
                if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
                    questions.append(current_question)
                else:
                    skipped += 1
                extra_html_parts = []

            marks_match = re.search(r"\((\d+)\s?(?:mks|marks?)\)", text, re.IGNORECASE)
            marks = int(marks_match.group(1)) if marks_match else 1
            clean_text = re.sub(r"\s*\(\d+\s?(?:mks|marks?)\)", "", text)
            question_text = re.sub(r"^\d+[\.\)]\s*", "", clean_text)

            current_question = {
                "question": question_text,
                "a": "", "b": "", "c": "", "d": "",
                "answer": "",
                "extra_content": None,
                "image": None,
                "marks": marks
            }

        # Detect options A–D
        elif re.match(r"^\(?[a-dA-D][\.\)]", text):
            match = re.match(r"^\(?([a-dA-D])[\.\)]\s*(.+)", text)
            if match and current_question:
                label = match.group(1).lower()
                content = match.group(2).strip()
                current_question[label] = content

        # Detect correct answer
        elif re.match(r"^(answer|correct answer):", text, re.IGNORECASE):
            match = re.search(r":\s*([a-dA-D])", text, re.IGNORECASE)
            if match and current_question:
                current_question["answer"] = match.group(1).lower()

        # Everything else becomes extra explanation
        elif questions_started:
            extra_html_parts.append(f"<p>{text}</p>")

    # Final question flush
    if current_question:
        current_question["extra_content"] = ''.join(extra_html_parts) if extra_html_parts else None
        if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
            questions.append(current_question)
        else:
            skipped += 1

    # Attach tables to the last question
    for table in document.tables:
        if questions:
            table_html = extract_table_html(table)
            questions[-1]["extra_content"] = (questions[-1].get("extra_content") or '') + table_html

    print(f"✅ Parsed {len(questions)} valid questions.")
    if skipped > 0:
        print(f"⚠️ Skipped {skipped} invalid questions.")

    return {
        "questions": questions
    }

def get_quiz_status(session, quiz_id, student_id):
    from models import Result
    result = session.query(Result).filter_by(quiz_id=quiz_id, student_id=student_id).first()
    return 'Completed' if result else 'Pending'