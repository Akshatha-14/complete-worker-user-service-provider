from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Remove duplicate email entries from WorkerApplication table'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking for duplicate emails...")
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Step 1: Find duplicates
                cursor.execute("""
                    SELECT email, COUNT(*) as count
                    FROM core_workerapplication
                    GROUP BY email
                    HAVING COUNT(*) > 1
                """)
                
                duplicates = cursor.fetchall()
                
                if not duplicates:
                    self.stdout.write(self.style.SUCCESS("✅ No duplicates found!"))
                    return
                
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️  Found {len(duplicates)} duplicate email(s):")
                )
                for email, count in duplicates:
                    self.stdout.write(f"   - {email}: {count} occurrences")
                
                # Step 2: For each duplicate email, handle foreign key constraints
                self.stdout.write("\n🔧 Handling foreign key constraints...")
                
                for email, _ in duplicates:
                    # Get all application IDs for this email
                    cursor.execute("""
                        SELECT id
                        FROM core_workerapplication
                        WHERE email = %s
                        ORDER BY created_at ASC
                    """, [email])
                    
                    app_ids = [row[0] for row in cursor.fetchall()]
                    keep_id = app_ids[0]  # Keep the oldest
                    delete_ids = app_ids[1:]  # Delete the rest
                    
                    self.stdout.write(f"\n  📧 {email}")
                    self.stdout.write(f"     Keeping ID: {keep_id}")
                    self.stdout.write(f"     Deleting IDs: {delete_ids}")
                    
                    # Update RazorpayPayments to point to the kept record
                    if delete_ids:
                        cursor.execute("""
                            UPDATE razorpay_payments
                            SET worker_application_id = %s
                            WHERE worker_application_id = ANY(%s)
                        """, [keep_id, delete_ids])
                        
                        updated_payments = cursor.rowcount
                        if updated_payments > 0:
                            self.stdout.write(f"     Updated {updated_payments} payment record(s)")
                
                # Step 3: Now delete duplicates (safe because foreign keys are updated)
                self.stdout.write("\n🗑️  Removing duplicate applications...")
                cursor.execute("""
                    DELETE FROM core_workerapplication
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM core_workerapplication
                        GROUP BY email
                    )
                """)
                
                deleted_count = cursor.rowcount
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Deleted {deleted_count} duplicate application(s)")
                )
                
                # Step 4: Verify no duplicates remain
                cursor.execute("""
                    SELECT email, COUNT(*) as count
                    FROM core_workerapplication
                    GROUP BY email
                    HAVING COUNT(*) > 1
                """)
                
                remaining = cursor.fetchall()
                if remaining:
                    self.stdout.write(
                        self.style.WARNING(f"\n⚠️  Warning: {len(remaining)} duplicate(s) still remain")
                    )
                else:
                    self.stdout.write(self.style.SUCCESS("\n✅ All duplicates removed successfully!"))
                    self.stdout.write("\n✨ You can now run: python manage.py migrate")
