import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set up environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

# Import required modules
from backend.app.workflow.graph import create_workflow, run_workflow
from backend.app.database import Base

async def test():
    # Setup test DB
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Run workflow
    task_id = "test-ai-dancing-123"
    message = "Tạo video nhảy AI dancing với ảnh input.jpeg, video mẫu videoinput.mp4 và nhạc dl_LaoSong3.mp3 trong thư mục input"
    
    print(f"Running workflow for message: {message}")
    # We need to insert the task into DB first to satisfy graph.py line 186
    from backend.app.models import AgentTask
    import datetime
    
    async with async_session() as session:
        task = AgentTask(
            task_id=task_id,
            workflow_type="ai_dancing",
            status="pending",
            input_data={"message": message},
            model_used="default",
            started_at=datetime.datetime.utcnow()
        )
        session.add(task)
        await session.commit()
    
    # We patch run_workflow's async_session to use ours if it's imported there
    import backend.app.workflow.graph
    backend.app.workflow.graph.async_session = async_session
    
    result = await run_workflow(task_id=task_id, message=message)
    print("Workflow completed. Result keys:", result.keys())
    print("Final Video URL:", result.get("final_video_url"))
    print("Final Video Path:", result.get("final_video_path"))
    print("Error:", result.get("error_message"))
    
if __name__ == "__main__":
    asyncio.run(test())
