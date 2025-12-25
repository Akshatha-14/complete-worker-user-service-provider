from datetime import date

def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
import random, string, os
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib.auth import get_user_model
from reportlab.pdfgen import canvas
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import WorkerApplication, Notification

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verifier2_submit(request, worker_id):
    try:
        app = WorkerApplication.objects.get(id=worker_id)
    except WorkerApplication.DoesNotExist:
        return Response({'error': 'Worker not found'}, status=404)

    # ✅ Find verified workers who can be assigned
    verified_workers = WorkerApplication.objects.filter(is_fully_verified=True)
    if not verified_workers.exists():
        return Response({'error': 'No verified workers available for assignment'}, status=400)

    assigned = random.choice(list(verified_workers))
    app.assigned_worker = assigned
    app.application_status = 'f2f_completed'
    app.save()

    # ✅ Email to applicant
    send_mail(
        subject="Face-to-Face Verification Completed",
        message=f"Hi {app.full_name}, your face-to-face verification is complete. "
                f"You are now assigned under {assigned.full_name}. They will contact you soon.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[app.email],
        fail_silently=True,
    )

    # ✅ Notify assigned worker
    Notification.objects.create(
        user=User.objects.get(email=assigned.email),
        title="New Worker Assigned",
        message=f"You have been assigned to verify {app.full_name} ({app.phone}). "
                f"Skills: {app.skills}. Experience: {app.experience}"
    )

    return Response({'message': 'F2F verification marked complete and assignment email sent.'})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assigned_worker_verify(request, worker_id):
    try:
        app = WorkerApplication.objects.get(id=worker_id)
    except WorkerApplication.DoesNotExist:
        return Response({'error': 'Worker not found'}, status=404)

    if not app.assigned_worker:
        return Response({'error': 'No assigned worker found'}, status=400)

    assigned = app.assigned_worker
    if request.user.email != assigned.email:
        return Response({'error': 'Not authorized'}, status=403)

    # ✅ Generate password
    password_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    from django.contrib.auth.hashers import make_password
    app.password_generated = make_password(password_plain)
    app.is_fully_verified = True
    app.application_status = 'fully_verified'
    app.save()

    # ✅ Generate PDF
    pdf_path = os.path.join(settings.MEDIA_ROOT, f"{app.full_name}_summary.pdf")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, f"Worker Verification Summary")
    c.drawString(100, 730, f"Name: {app.full_name}")
    c.drawString(100, 710, f"Phone: {app.phone}")
    c.drawString(100, 690, f"Location: {app.location}")
    c.drawString(100, 670, f"Skills: {app.skills}")
    c.drawString(100, 650, f"Experience: {app.experience}")
    c.save()

    # ✅ Email to worker
    mail = EmailMessage(
        subject="Verification Completed – Welcome!",
        body=f"Hi {app.full_name},\n\nCongratulations! All verifications are complete.\n"
             f"Your login password: {password_plain}\n\nYour summary PDF is attached.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[app.email],
    )
    mail.attach_file(pdf_path)
    mail.send(fail_silently=True)

    return Response({'message': 'Final verification done, email sent.'})

