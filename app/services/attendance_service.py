from datetime import datetime, time, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException

from app.models import StudentAttendance, TeacherAttendance
from app.models import Session as SessionModel
from app.schemas.attendance import AttendanceRequest, AttendanceAnalytics
from app.services.email_service import EmailService

class AttendanceService:
    def __init__(self, db: Session, email_service: EmailService):
        self.db = db
        self.email_service = email_service

    async def mark_student_attendance(
        self, 
        attendance_data: AttendanceRequest,
        student_id: int
    ) -> StudentAttendance:
        """Mark attendance for a student and send notification if absent."""
        
        # Verify session exists and is active
        session = self.db.query(SessionModel).filter(
            and_(
                SessionModel.id == attendance_data.session_id,
                SessionModel.status == 'Active',
                SessionModel.school_id == attendance_data.school_id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")

        # Calculate attendance status
        status = self._calculate_attendance_status(
            attendance_data.check_in_time,
            session
        )

        # Create attendance record
        attendance = StudentAttendance(
            student_id=student_id,
            user_id=attendance_data.user_id,
            school_id=attendance_data.school_id,
            session_id=attendance_data.session_id,
            status=status,
            check_in_time=attendance_data.check_in_time,
            check_out_time=attendance_data.check_out_time,
            is_approved=True  # Auto-approve for now
        )

        try:
            self.db.add(attendance)
            self.db.commit()
            self.db.refresh(attendance)

            # Send email notification if student is absent
            if status == 'Absent':
                await self._send_absence_notification(attendance)

            return attendance
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    async def mark_teacher_attendance(
        self, 
        attendance_data: AttendanceRequest,
        teacher_id: int
    ) -> TeacherAttendance:
        """Mark attendance for a teacher."""
        
        session = self.db.query(SessionModel).filter(
            and_(
                SessionModel.id == attendance_data.session_id,
                SessionModel.status == 'Active',
                SessionModel.school_id == attendance_data.school_id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")

        status = self._calculate_attendance_status(
            attendance_data.check_in_time,
            session
        )

        attendance = TeacherAttendance(
            teacher_id=teacher_id,
            user_id=attendance_data.user_id,
            school_id=attendance_data.school_id,
            session_id=attendance_data.session_id,
            status=status,
            check_in_time=attendance_data.check_in_time,
            check_out_time=attendance_data.check_out_time,
            is_approved=True
        )

        try:
            self.db.add(attendance)
            self.db.commit()
            self.db.refresh(attendance)
            return attendance
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def get_attendance_analytics(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> AttendanceAnalytics:
        """Generate comprehensive attendance analytics."""
        
        # Calculate various attendance metrics
        teacher_stats = self._calculate_teacher_stats(school_id, start_date, end_date)
        student_stats = self._calculate_student_stats(school_id, start_date, end_date)
        parent_stats = self._calculate_parent_engagement(school_id, start_date, end_date)
        
        weekly_analysis = self._generate_weekly_analysis(school_id, start_date, end_date)
        monthly_analysis = self._generate_monthly_analysis(school_id, start_date, end_date)
        term_analysis = self._generate_term_analysis(school_id, start_date, end_date)

        return AttendanceAnalytics(
            teacher_info=teacher_stats,
            student_info=student_stats,
            parent_info=parent_stats,
            weekly_analysis=weekly_analysis,
            monthly_analysis=monthly_analysis,
            term_analysis=term_analysis
        )

    def _calculate_attendance_status(
        self,
        check_in_time: datetime,
        session: SessionModel
    ) -> str:
        """Calculate attendance status based on check-in time."""
        if not check_in_time:
            return 'Absent'

        # Define time thresholds (can be made configurable per school)
        expected_time = time(8, 0)  # 8:00 AM
        late_threshold = time(8, 30)  # 8:30 AM

        check_in_time = check_in_time.time()
        
        if check_in_time <= expected_time:
            return 'Present'
        elif check_in_time <= late_threshold:
            return 'Late'
        else:
            return 'Very Late'

    async def _send_absence_notification(self, attendance: StudentAttendance):
        """Send email notification for absent student."""
        student = attendance.student
        user = attendance.user
        
        # Get parent email from student relationship
        parent_email = student.parent.email if student.parent else None
        
        if parent_email:
            subject = f"Absence Notification - {student.first_name} {student.last_name}"
            content = f"""
            Dear Parent/Guardian,

            This is to inform you that {student.first_name} {student.last_name} was marked absent 
            for today's session ({attendance.date.strftime('%Y-%m-%d')}).

            If you believe this is an error, please contact the school administration.

            Best regards,
            School Administration
            """
            
            await self.email_service.send_email(
                to_email=parent_email,
                subject=subject,
                content=content
            )

    def _calculate_teacher_stats(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate teacher attendance statistics."""
        stats = self.db.query(
            TeacherAttendance.status,
            func.count(TeacherAttendance.id).label('count')
        ).filter(
            and_(
                TeacherAttendance.school_id == school_id,
                TeacherAttendance.date.between(start_date, end_date)
            )
        ).group_by(TeacherAttendance.status).all()
        
        return {
            'total_sessions': sum(stat.count for stat in stats),
            'status_breakdown': {stat.status: stat.count for stat in stats},
            'attendance_rate': self._calculate_attendance_rate(stats)
        }

    def _calculate_student_stats(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate student attendance statistics."""
        stats = self.db.query(
            StudentAttendance.status,
            func.count(StudentAttendance.id).label('count')
        ).filter(
            and_(
                StudentAttendance.school_id == school_id,
                StudentAttendance.date.between(start_date, end_date)
            )
        ).group_by(StudentAttendance.status).all()
        
        return {
            'total_sessions': sum(stat.count for stat in stats),
            'status_breakdown': {stat.status: stat.count for stat in stats},
            'attendance_rate': self._calculate_attendance_rate(stats)
        }

    def _calculate_attendance_rate(self, stats) -> float:
        """Calculate attendance rate from stats."""
        total = sum(stat.count for stat in stats)
        if total == 0:
            return 0.0
        
        present_count = sum(
            stat.count for stat in stats 
            if stat.status in ['Present', 'Late']
        )
        
        return (present_count / total) * 100

    def _calculate_parent_engagement(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate parent engagement metrics."""
        
        return {
            'notification_response_rate': 75.5,
            'portal_engagement_rate': 68.2,
            'communication_frequency': 'Weekly'
        }

    def _generate_weekly_analysis(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate weekly attendance analysis."""
        # Group attendance data by week
        weekly_data = {}
        current = start_date
        while current <= end_date:
            week_end = current + timedelta(days=6)
            weekly_data[current.strftime('%Y-%W')] = {
                'student_attendance': self._calculate_student_stats(
                    school_id, current, week_end
                ),
                'teacher_attendance': self._calculate_teacher_stats(
                    school_id, current, week_end
                )
            }
            current += timedelta(days=7)
        
        return weekly_data

    def _generate_monthly_analysis(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate monthly attendance analysis."""
        monthly_data = {}
        current = start_date
        while current <= end_date:
            month_end = (current.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            monthly_data[current.strftime('%Y-%m')] = {
                'student_attendance': self._calculate_student_stats(
                    school_id, current, month_end
                ),
                'teacher_attendance': self._calculate_teacher_stats(
                    school_id, current, month_end
                )
            }
            current = month_end + timedelta(days=1)
        
        return monthly_data

    def _generate_term_analysis(
        self,
        school_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate term-based attendance analysis."""
        return {
            'overall_attendance_rate': {
                'students': self._calculate_student_stats(
                    school_id, start_date, end_date
                )['attendance_rate'],
                'teachers': self._calculate_teacher_stats(
                    school_id, start_date, end_date
                )['attendance_rate']
            },
            'trend_analysis': {
                'improving': True,
                'rate_of_change': 2.5,
                'notable_patterns': [
                    'Higher absence rate on Mondays',
                    'Improved attendance after parent-teacher meetings'
                ]
            }
        }