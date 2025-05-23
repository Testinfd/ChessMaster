import re
from struct import pack
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import DATABASE_URI, DATABASE_NAME, COURSES_COLLECTION, FILES_COLLECTION
from .db_helpers import get_mongo_client

client = get_mongo_client(DATABASE_URI)
db = client[DATABASE_NAME]
courses_col = db[COURSES_COLLECTION]
files_col = db[FILES_COLLECTION]

async def save_course(course_data):
    """Save a new course in the database."""
    if courses_col.find_one({'course_id': course_data['course_id']}):
        return False, 0
    
    try:
        courses_col.insert_one(course_data)
        return True, 1
    except DuplicateKeyError:
        return False, 0
    except Exception as e:
        print(f"Error saving course: {e}")
        return False, 0

async def save_course_file(file_data):
    """Save a file related to a course."""
    try:
        files_col.insert_one(file_data)
        return True
    except Exception as e:
        print(f"Error saving course file: {e}")
        return False

async def get_course_by_id(course_id):
    """Get course details by course ID."""
    return courses_col.find_one({'course_id': course_id})

async def get_course_by_name(course_name):
    """Get course by name (exact match)."""
    return courses_col.find_one({'course_name': course_name})

async def get_course_files(course_id):
    """Get all files related to a course by course ID."""
    files = []
    cursor = files_col.find({'course_id': course_id}).sort('file_order', 1)
    for file in cursor:
        files.append(file)
    return files

async def search_courses(query, max_results=10, offset=0):
    """Search for courses by name."""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    filter = {'course_name': regex}
    
    courses = []
    cursor = courses_col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)
    
    for course in cursor:
        courses.append(course)
        
    total_results = courses_col.count_documents(filter)
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    
    return courses, next_offset, total_results

async def update_course(course_id, update_data):
    """Update a course's details."""
    try:
        courses_col.update_one({'course_id': course_id}, {'$set': update_data})
        return True
    except Exception as e:
        print(f"Error updating course: {e}")
        return False

async def delete_course(course_id):
    """Delete a course and all its files."""
    try:
        courses_col.delete_one({'course_id': course_id})
        files_col.delete_many({'course_id': course_id})
        return True
    except Exception as e:
        print(f"Error deleting course: {e}")
        return False

async def get_all_courses(max_results=100, offset=0):
    """Get all courses with pagination."""
    courses = []
    cursor = courses_col.find().sort('$natural', -1).skip(offset).limit(max_results)
    
    for course in cursor:
        courses.append(course)
        
    total_results = courses_col.count_documents({})
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    
    return courses, next_offset, total_results 