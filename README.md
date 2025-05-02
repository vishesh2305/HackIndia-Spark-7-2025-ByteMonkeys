Aidly is a secure and AI-powered Crowdfunding platform that help users raise funds through verified campaigns without charging any platform fee.
Aidly ensure that no fake users can start campaign , so users have to go through a verification process , where their details and pic is verified with any government ID provided.
Users cannot start the campaign, they can send a request ,then the request is validated through AI sentimental Analysis.
If approved , campaigns go live and recieve donations via PayPal.
Aidly ensures 100% of donetions reach the recipint . 
TECH USED => 
Face Recognition - We have used Flask for building APIs,  python library face_recognition , Pillow(PIL) for image processing, Base64 handling for decoding base64 image strings , numpy for cenverting images into array , logging for error tracking , IO operations for converting in-memory byte streams into file like objects.

OCR VALIDATION - We have useed pytesseract fro data extraction from the image , pillow(PIL) for image processing and then it validate the OCR with the user's provided document. If it matches only then it will proceed to the Main WebInterface.

On the Campaign Creation page The user can Create Campaigns . The campaigns are stored in blockchain and the storage is Used IPFS for decentralization and MongoDB's secure Database.

Also there is a feature of Sentimant Analysis , if the Sentiment Analysis Score is zero then it will not proceed to the Creating a Campaign and for this we used google's search to Scrap the Web, and then Analyze its sentimental score. 

If the Campaign Verifies then users can fund on the campaign through Two methods, Via: Blockchain Wallet, and Paypal. 

Thus the Project is fully secure , reliable for every user.
