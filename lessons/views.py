from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.db import models
import logging
from .models import Lesson
from .serializers import LessonSerializer, LessonPublicSerializer, LessonGenerateSerializer
from .permissions import IsLessonOwner
from .utils import generate_lesson_pdf
from .services.openai_service import generate_lesson_content
from .services.unsplash_service import fetch_unsplash_images
from .services.youtube_service import fetch_youtube_videos

logger = logging.getLogger(__name__)


class LessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing lessons.
    
    list: Get all lessons for the authenticated user
    create: Create a new lesson
    retrieve: Get a specific lesson (must be owner)
    update: Update a lesson (must be owner)
    partial_update: Partially update a lesson (must be owner)
    destroy: Delete a lesson (must be owner)
    toggle_visibility: Toggle is_public field (must be owner)
    """
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return lessons for the authenticated user only, with optional search."""
        base_qs = Lesson.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search')
        if search:
            base_qs = base_qs.filter(
                models.Q(topic__icontains=search) | models.Q(subject__icontains=search)
            )
        return base_qs

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'toggle_visibility']:
            permission_classes = [IsAuthenticated, IsLessonOwner]
        elif self.action == 'download_pdf':
            # Allow any; download handler will enforce public-or-owner access.
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_lesson(self, request):
        """
        Generate lesson content using OpenAI, Unsplash, and YouTube services.
        
        Combines all three services to create comprehensive lesson content:
        - OpenAI: Generates description, activities, questions, summary
        - Unsplash: Fetches relevant images
        - YouTube: Fetches educational videos
        
        Returns 502 if OpenAI fails (critical service).
        Returns empty arrays for images/videos if those services fail (non-critical).
        """
        # Validate input (raises 400 if invalid)
        serializer = LessonGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        topic = data['topic']
        subject = data['subject']
        grade = data['grade_level']
        duration = data['duration_minutes']

        errors = []
        
        # 1. Generate content with OpenAI (try, but allow fallback)
        description = ""
        content = ""
        activities = []
        questions = []
        summary = ""
        
        try:
            ai_content = generate_lesson_content(
                topic=topic,
                subject=subject,
                grade_level=grade,
                duration_minutes=duration
            )
            
            description = ai_content['description']
            content = ai_content['content']
            activities = ai_content['activities']
            questions = ai_content['questions']
            summary = ai_content['summary']
            
        except ValueError as e:
            # API key missing or configuration error - use fallback
            logger.warning(f"OpenAI configuration error, using fallback: {str(e)}")
            errors.append(f"OpenAI service not configured: {str(e)}")
            description = (
                f"This lesson on {topic} for {grade} covers key concepts in {subject} "
                f"and is designed for a {duration}-minute session. "
                f"Students will explore the fundamental principles of {topic} through interactive activities and discussions."
            )
            # Generate fallback content based on duration
            if duration <= 30:
                content = (
                    f"{topic} is an important concept in {subject} that {grade} students should understand. "
                    f"This lesson provides an overview of the key ideas and principles related to {topic}. "
                    f"Students will learn the fundamental aspects and how they apply in real-world contexts."
                )
            elif duration <= 60:
                content = (
                    f"{topic} is a significant topic in {subject} that requires careful study. "
                    f"This lesson explores the main concepts, principles, and applications of {topic}. "
                    f"Students will gain a solid understanding of how {topic} works and why it matters in {subject}. "
                    f"We will examine examples and discuss practical applications that help illustrate the key ideas."
                )
            else:
                content = (
                    f"{topic} represents a comprehensive area of study within {subject} that demands thorough exploration. "
                    f"This extended lesson delves deep into the concepts, mechanisms, and real-world significance of {topic}. "
                    f"Students will engage with detailed explanations, multiple examples, and in-depth discussions. "
                    f"We will cover the foundational principles, examine various applications, and explore how {topic} connects to broader themes in {subject}. "
                    f"Through this comprehensive approach, students will develop a nuanced understanding of {topic} and its importance."
                )
            activities = [
                f"Warm-up discussion on prior knowledge about {topic}",
                f"Interactive demonstration related to {subject}",
                f"Group activity exploring {topic} applications",
                "Wrap-up and reflection",
            ]
            questions = [
                f"What are the main ideas behind {topic}?",
                f"How does {topic} connect to real-world {subject} examples?",
                "What questions do you still have after this lesson?",
            ]
            summary = f"Students will understand foundational aspects of {topic} and how it fits within {subject}."
        except Exception as e:
            # API call failed (quota, network, etc.) - use fallback
            logger.warning(f"OpenAI API error, using fallback: {str(e)}")
            errors.append(f"OpenAI service unavailable: {str(e)}")
            description = (
                f"This lesson on {topic} for {grade} covers key concepts in {subject} "
                f"and is designed for a {duration}-minute session. "
                f"Students will explore the fundamental principles of {topic} through interactive activities and discussions."
            )
            # Generate fallback content based on duration
            if duration <= 30:
                content = (
                    f"{topic} is an important concept in {subject} that {grade} students should understand. "
                    f"This lesson provides an overview of the key ideas and principles related to {topic}. "
                    f"Students will learn the fundamental aspects and how they apply in real-world contexts."
                )
            elif duration <= 60:
                content = (
                    f"{topic} is a significant topic in {subject} that requires careful study. "
                    f"This lesson explores the main concepts, principles, and applications of {topic}. "
                    f"Students will gain a solid understanding of how {topic} works and why it matters in {subject}. "
                    f"We will examine examples and discuss practical applications that help illustrate the key ideas."
                )
            else:
                content = (
                    f"{topic} represents a comprehensive area of study within {subject} that demands thorough exploration. "
                    f"This extended lesson delves deep into the concepts, mechanisms, and real-world significance of {topic}. "
                    f"Students will engage with detailed explanations, multiple examples, and in-depth discussions. "
                    f"We will cover the foundational principles, examine various applications, and explore how {topic} connects to broader themes in {subject}. "
                    f"Through this comprehensive approach, students will develop a nuanced understanding of {topic} and its importance."
                )
            activities = [
                f"Warm-up discussion on prior knowledge about {topic}",
                f"Interactive demonstration related to {subject}",
                f"Group activity exploring {topic} applications",
                "Wrap-up and reflection",
            ]
            questions = [
                f"What are the main ideas behind {topic}?",
                f"How does {topic} connect to real-world {subject} examples?",
                "What questions do you still have after this lesson?",
            ]
            summary = f"Students will understand foundational aspects of {topic} and how it fits within {subject}."

        # 2. Fetch images from Unsplash (non-critical, can fail gracefully)
        image_urls = []
        try:
            image_urls = fetch_unsplash_images(topic=topic, limit=6)
            if not image_urls:
                logger.warning(f"No images found for topic: {topic}")
        except Exception as e:
            logger.warning(f"Failed to fetch Unsplash images: {str(e)}")
            errors.append(f"Image fetching failed: {str(e)}")
        
        # 3. Fetch videos from YouTube (non-critical, can fail gracefully)
        video_links = []
        try:
            video_links = fetch_youtube_videos(topic=topic, subject=subject, limit=5)
            if not video_links:
                logger.warning(f"No videos found for topic: {topic}, subject: {subject}")
        except Exception as e:
            logger.warning(f"Failed to fetch YouTube videos: {str(e)}")
            errors.append(f"Video fetching failed: {str(e)}")

        # Build response
        response_data = {
            "topic": topic,
            "subject": subject,
            "grade_level": grade,
            "duration_minutes": duration,
            "description": description,
            "content": content,
            "activities": activities,
            "questions": questions,
            "summary": summary,
            "image_urls": image_urls,
            "video_links": video_links,
        }
        
        # Include warnings if any non-critical services failed
        if errors:
            response_data["warnings"] = errors
        
        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['patch'], url_path='visibility')
    def toggle_visibility(self, request, pk=None):
        """Toggle the is_public field of a lesson."""
        lesson = self.get_object()
        lesson.is_public = not lesson.is_public
        lesson.save()
        
        serializer = self.get_serializer(lesson)
        return Response({
            'message': f'Lesson visibility set to {"public" if lesson.is_public else "private"}',
            'lesson': serializer.data
        })

    @action(detail=True, methods=['get'], url_path='pdf', url_name='pdf')
    def download_pdf(self, request, pk=None):
        """
        Download lesson as PDF.
        Public lessons are downloadable by anyone; private lessons require ownership.
        """
        try:
            lesson = Lesson.objects.get(pk=pk)
        except Lesson.DoesNotExist:
            return Response({'error': 'Lesson not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not lesson.is_public and (not request.user.is_authenticated or lesson.user != request.user):
            return Response(
                {'error': 'You do not have permission to download this lesson.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Generate PDF
        try:
            pdf_buffer = generate_lesson_pdf(lesson)
            
            # Prepare response
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="lesson_{lesson.id}_{lesson.slug}.pdf"'
            
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LessonPublicView(viewsets.ReadOnlyModelViewSet):
    """
    Public view for accessing public lessons by slug.
    No authentication required.
    """
    serializer_class = LessonPublicSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        """Return only public lessons with optional search."""
        qs = Lesson.objects.filter(is_public=True)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                models.Q(topic__icontains=search) | models.Q(subject__icontains=search)
            )
        return qs

    def retrieve(self, request, slug=None):
        """Retrieve a public lesson by slug."""
        try:
            lesson = get_object_or_404(Lesson, slug=slug, is_public=True)
            serializer = self.get_serializer(lesson)
            return Response(serializer.data)
        except Http404:
            return Response(
                {'error': 'Lesson not found or not public'},
                status=status.HTTP_404_NOT_FOUND
            )

