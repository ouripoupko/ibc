import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { Contract, Method } from './contract';
import { MessageService } from './message.service';

@Injectable({
  providedIn: 'root'
})
export class ContractService {

  private contractUrl = 'contract';
  httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  constructor(
    private http: HttpClient,
    private messageService: MessageService) { }

  private log(message: string) {
    this.messageService.add(`contractService: ${message}`);
  }

  getIdentities(): Observable<string[]> {
    return this.http.get<string[]>('app').pipe(
      tap(_ => this.log(`fetched identities`)),
    );
  }

  setIdentity(name: string): Observable<string[]> {
    return this.http.post<string[]>(`app/${name}`, {}, this.httpOptions).pipe(

      tap(_ => this.log('added new identity')),
      catchError(this.handleError<string[]>('setIdentity'))
    );
  }

  /** GET **/
  getContracts(agent): Observable<Contract[]> {
    return this.http.get<Contract[]>(`app/${agent}`)
      .pipe(
        tap(_ => this.log('fetched contracts')),
        catchError(this.handleError<Contract[]>('getContracts', []))
      );
  }

  /** POST **/
  addContract(agent: string, name: string, contract: Contract): Observable<Contract> {
    return this.http.post<Contract>(`app/${agent}/${name}`, contract, this.httpOptions).pipe(
      tap((newContract: Contract) => this.log(`added contract with name=${newContract.name}`)),
      catchError(this.handleError<Contract>('addContract'))
    );
  }

  /** GET **/
  getContract(agent: string, name: string): Observable<Contract> {
    return this.http.get<Contract>(`app/${agent}/${name}`).pipe(
      tap((newContract: Contract) => this.log(`fetched contract name=${name}`)),
      catchError(this.handleError<Contract>(`getContract name=${name}`))
    );
  }

  /** PUT **/
  callContract(agent: string, contract: string, method: string, args: Method): Observable<any> {
    if(method.startsWith('get_')) {
      return this.http.post<Contract>(`app/${agent}/${contract}/${method}`, args, this.httpOptions).pipe(
        tap(_ => this.log(`called contract name=${contract} method=${method}`)),
        catchError(this.handleError<any>('callContract'))
      );
    }
    return this.http.put<Contract>(`app/${agent}/${contract}/${method}`, args, this.httpOptions).pipe(
      tap(_ => this.log(`called contract name=${contract} method=${method}`)),
      catchError(this.handleError<any>('callContract'))
    );
  }

  /** POST **/
  connect(agent: string, address: string, pid: string, name: string): Observable<any> {
    return this.http.post(`app/${agent}/${name}`, { address: address, pid: pid }, this.httpOptions).pipe(
      tap(_ => this.log(`connected to ${address} with contract ${name}`)),
      catchError(this.handleError<any>('connect'))
    );
  }

  /**
   * Handle Http operation that failed.
   * Let the app continue.
   * @param operation - name of the operation that failed
   * @param result - optional value to return as the observable result
  */
  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {

      // TODO: send the error to remote logging infrastructure
      console.error(error); // log to console instead

      // TODO: better job of transforming error for user consumption
      this.log(`${operation} failed: ${error.message}`);

      // Let the app keep running by returning an empty result.
      return of(result as T);
    };
  }
}
