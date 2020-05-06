import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import func
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

def paginate(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)
  
    CORS(app, resources={r'*': {'origins': '*'}})

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                            'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods',
                           'GET, POST, PATCH, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response


    @app.route('/categories', methods=['GET'])
    def get_categories():
        try:
            categories = Category.query.all()
            if (len(categories) == 0):
                  abort(404)

            formatted_categories = {
                category.id: category.type for category in categories
            }

            return jsonify({
                'succes': True,
                'categories': formatted_categories,
                'total_categories': len(Category.query.all())
            })

        except Exception:
            abort(422)


    @app.route('/questions', methods=['GET'])
    def get_questions():
        selection = Question.query.order_by(Question.id).all()
        current_questions = paginate(request, selection)

        print(len(current_questions))

        if len(current_questions) == 0:
            abort(404)

        categories = {
            category.id: category.type for category in Category.query.all()
        }

        return jsonify({
            'succes': True,
            'questions': current_questions,
            'total_questions': len(Question.query.all()),
            'current_category': [],
            'categories': categories
        })

    @app.route('/questions/<int:question_id>', methods=['DELETE'])
    def delete_question(question_id):
        question_to_del = Question.query.filter(
            Question.id == question_id).one_or_none()
        if question_to_del is None:
            abort(404)
        
        try:
            question_to_del.delete()

            return jsonify({
                'success': True,
                'question': question_to_del,
                'total_questions': len(Question.query.all())
            })

        except Exception:
            abort(422)

    @app.route('/questions', methods=['POST'])    
    def create_question():     
        body = request.get_json()

        new_question = body.get('question', None)
        new_answer = body.get('answer', None)
        new_difficulty = body.get('difficulty', None)
        new_category = body.get('category', None)
        search_term = body.get('searchTerm', None) 

        try:
            if search_term:  # handles search
                selection = Question.query.order_by(Question.id).filter(
                    Question.question.ilike('%{}%'.format(search_term)))
                current_questions = paginate(request, selection)

                if len(current_questions) == 0:
                    abort(404)
                else:
                    return jsonify({
                        'questions': current_questions,
                        'total_questions': len(Question.query.all()),
                        'current_category': [(question['category'])
                                             for question in current_questions]
                    })
            else:  # handles creation of new question
                question = Question(question=new_question,
                                    answer=new_answer,
                                    difficulty=new_difficulty,
                                    category=new_category)
                question.insert()

                selection = Question.query.order_by(Question.id).all()
                questions = paginate(request, selection)

                return jsonify({
                    'success': True,
                    'questions': questions,
                    'created': question.id,
                    'total_questions': len(Question.query.all())
                })

        except Exception:
            abort(422)    


    @app.route('/questions/search', methods=['POST'])
    def search_for_questions():
        body = request.get_json()
        search_term = body.get('searchTerm', None)

        if search_term:
            search_results = Question.query.filter(
                Question.question.ilike(f'%{search_term}%')).all()

            return jsonify({
                'success': True,
                'questions': [question.format() for question in search_results],
                'total_questions': len(search_results),
                'current_category': None
            })
        
        abort(404)

    @app.route('/categories/<int:category_id>/questions', methods=['GET'])
    def get_questions_categories(category_id):
        current_category = Category.query.filter(Category.id == category_id).one_or_none()

        if current_category is None:
            abort(404)

        selection = Question.query.filter(Question.category == category_id).all()
        current_questions = paginate(request, selection)

        if len(current_questions) == 0:
            abort(404)

        return jsonify({
            'success': True,
            'questions': current_questions,
            'total_questions': len(Question.query.all()),
            'current_category': current_category
        })

    @app.route('/quizzes', methods=['POST'])
    def get_quizzes():
        try:
            body = request.get_json()
            previous_questions = body.get('previous_questions', None)
            quiz_category = body.get('quiz_category', None)

            category_id = int(quiz_category['id'])

            if len(previous_questions) > 0:
                if category_id > 0:
                    current_question = Question.query.filter(
                        Question.category == category_id)\
                            .filter(~Question.id.in_(previous_questions))\
                            .order_by(func.random()).first()
                    
                else:
                    current_question = Question.query.filter(~Question.id.in_(
                        previous_questions)).order_by(func.random()).first()

            else:
                if category_id > 0:
                    current_question = Question.query.filter(
                        Question.category == quiz_category['id'])\
                            .order_by(func.random()).first()
                else:
                    current_question = Question.query.order_by(
                        func.random()).first()
            
            if current_question is not None:
                formatted_question = current_question.format()
            else:
                formatted_question = None
            
            return jsonify({
                'success': True,
                'question': formatted_question
            })

        except Exception:
            abort(404)


    @app.errorhandler(422)
    def unprocessable_error_handler(error):
        return jsonify({
            'success': False,
            'message': 'unprocessable'
        })
  
    @app.errorhandler(404)
    def resource_not_found_error_handler(error):
        return jsonify({
            'success': False,
            'message': 'resource not found'
        })

    @app.errorhandler(400)
    def bad_request_error_handler(error):
        return jsonify({
            'success': False,
            'message': 'bad request'
        })

    @app.errorhandler(405)
    def method_not_allowed_error_handler(error):
        return jsonify({
            'success': False,
            'message': 'method not allowed'
        })

    @app.errorhandler(500)
    def internal_server_error_handler(error):
        return jsonify({
            'success': False,
            'message': 'internal server error'
        })

    return app

    