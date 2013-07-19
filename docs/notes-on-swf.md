=======
Notes on SWF
=========

Simple Work Flow manages workflow state. 


* Deciders will handle more than the default 100 event history items returned by one polling request to SWF by following nextPageTokens until the complete event history is assembled.
