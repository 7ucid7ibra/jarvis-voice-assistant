I created this simple voice assistant that can use a [[L-LLM]], but also can be setup using an API key and a [[local text-to-speech]] and speech-to-text AI that was able to send commands to my Raspberry Pi 3 running the Home Assistant OS to control a virtual switch. 

It has a simple GUI with a record button, and a chat window for recent history, a settings button, and opens a model to edit some settings, and a close button. That's it. 

It works fundamentally, but there are still some bugs. Sometimes it doesn't work, sometimes the speech-to-text isn't very accurate. Sometimes the AI forgets its role and refuses to do the command or says it is not capable of doing so. Or it forgets the context of the conversation randomly.

I tried to set up a [[multi-agent system]], but also this system had some issues, since AIs mostly think humans give input. So since AI was giving input to AI, it then started mixing up the roles.

For example, once I told it to remember my name, it retained my name, and when I asked it for my name, it said that its name was my name. Because I gave the request, an agent interpreted my request, gave a request to a next agent who assumed that it was a human, and then answered that the user's name is bob.
so it took the answer of the previous AI - that the user's name is Bob and named itself Bob and then answered the actual user saying that it was Bob, instead of the user. 

So there are definitely still some areas that need improvement, but the general concept of voice controlling on AI that can wirelessly control smart home appliances and retain information about the user works.