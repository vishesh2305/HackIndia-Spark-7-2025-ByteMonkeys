import React, { useState, useEffect } from 'react';
import { fetchOCRValidation } from '../utils/api'; // Function to call backend
import { initWeb3, storeHashOnChain } from '../utils/web3'; // Blockchain functions

function OCRInput({ imageId }) {
    const [name, setName] = useState('');
    const [dob, setDob] = useState('');
    const [aadhar, setAadhar] = useState('');
    const [validationResult, setValidationResult] = useState(null);
    const [web3Initialized, setWeb3Initialized] = useState(false);

    useEffect(() => {
        const initializeWeb3 = async () => {
            const success = await initWeb3();
            setWeb3Initialized(success);
        };
        initializeWeb3();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();

        const userData = { name, dob, aadhar, imageId };

        try {
            const ocrResult = await fetchOCRValidation(userData);

            if (ocrResult.is_valid) {
                setValidationResult({
                    message: ocrResult.message,
                    details: ocrResult.details,
                    type: 'success',
                });

                if (web3Initialized) {
                    const dataToHash = { name: ocrResult.name, id_number: ocrResult.id_number };
                    const dataHash = await hashData(dataToHash); // Implement this in utils/web3.js

                    const txHash = await storeHashOnChain(dataHash);

                    if (txHash) {
                        setValidationResult((prevResult) => ({
                            ...prevResult,
                            txHash,
                            blockchainMessage: 'Data hash stored on blockchain!',
                        }));
                    } else {
                        setValidationResult((prevResult) => ({
                            ...prevResult,
                            blockchainMessage: 'Error storing data hash on blockchain.',
                        }));
                    }
                } else {
                    setValidationResult((prevResult) => ({
                        ...prevResult,
                        blockchainMessage: 'Web3 not initialized. Data hash not stored on blockchain.',
                    }));
                }
            } else {
                setValidationResult({
                    message: ocrResult.message,
                    details: ocrResult.details,
                    type: 'error',
                });
            }
        } catch (error) {
            console.error('Error during OCR validation:', error);
            setValidationResult({
                message: 'Error processing OCR validation.',
                details: error.message,
                type: 'error',
            });
        }
    };

    return (
        <div>
            {validationResult && (
                <div className={validationResult.type === 'success' ? 'success' : 'error'}>
                    <p>{validationResult.message}</p>
                    <p>{validationResult.details}</p>
                    {validationResult.blockchainMessage && (
                        <p>{validationResult.blockchainMessage}: {validationResult.txHash}</p>
                    )}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                <label htmlFor="name">Name:</label>
                <input type="text" id="name" value={name} onChange={(e) => setName(e.target.value)} />

                <label htmlFor="dob">Date of Birth:</label>
                <input type="text" id="dob" value={dob} onChange={(e) => setDob(e.target.value)} />

                <label htmlFor="aadhar">Aadhar Number:</label>
                <input type="text" id="aadhar" value={aadhar} onChange={(e) => setAadhar(e.target.value)} />

                <button type="submit">Validate</button>
            </form>
        </div>
    );
}

export default OCRInput;